"""
Telegram Channel Scraper - Production-Grade ELT Pipeline (Extract & Load)
Task-1: Data Scraping & Collection for medical-telegram-warehouse

This module implements idempotent, non-blocking Telegram data extraction
with proper error handling, logging, and data lake storage.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiofiles
from dotenv import load_dotenv
from telethon import TelegramClient, errors
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# Load environment variables
load_dotenv()

# Configuration
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME', 'telegram_scraper')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE')  # Optional: for non-interactive mode
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Optional: no phone/code needed
DRY_RUN = os.getenv('DRY_RUN', '').lower() in ('1', 'true', 'yes')  # Skip Telegram, write sample data
CHANNELS_STR = os.getenv('TELEGRAM_CHANNELS', 'CheMed,Lobelia Cosmetics,Tikvah Pharma')
MAX_MESSAGES = int(os.getenv('MAX_MESSAGES_PER_CHANNEL', '1000'))
BATCH_SIZE = int(os.getenv('SCRAPER_BATCH_SIZE', '100'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = os.getenv('LOG_DIR', 'logs')
DATA_RAW_MESSAGES = os.getenv('DATA_RAW_MESSAGES', 'data/raw/telegram_messages')
DATA_RAW_IMAGES = os.getenv('DATA_RAW_IMAGES', 'data/raw/images')

# Parse channels list
CHANNELS = [ch.strip() for ch in CHANNELS_STR.split(',') if ch.strip()]

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = f"{LOG_DIR}/scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TelegramScraper:
    """
    Production-grade Telegram scraper with idempotent operations,
    error handling, and data lake storage.
    """

    def __init__(self):
        """Initialize the scraper with Telegram client."""
        if not API_ID or not API_HASH:
            raise ValueError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env file. "
                "Use mock/sandbox credentials for development."
            )

        self.client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
        self.data_messages_dir = Path(DATA_RAW_MESSAGES)
        self.data_images_dir = Path(DATA_RAW_IMAGES)
        
        # Create directory structure
        self.data_messages_dir.mkdir(parents=True, exist_ok=True)
        self.data_images_dir.mkdir(parents=True, exist_ok=True)

    async def connect(self):
        """Establish connection to Telegram."""
        try:
            # Bot token: no phone or verification code needed (use production API + token from @BotFather)
            if TELEGRAM_BOT_TOKEN:
                logger.info("Connecting with bot token (no phone or code required)")
                await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
            # Phone from env (non-interactive until code prompt)
            elif TELEGRAM_PHONE:
                logger.info(f"Connecting with phone from environment: {TELEGRAM_PHONE[:3]}***")
                await self.client.start(phone=TELEGRAM_PHONE)
            else:
                logger.info("Connecting in interactive mode (will prompt for phone)")
                await self.client.start()
            logger.info("Successfully connected to Telegram")
            return True
        except errors.SessionPasswordNeededError:
            logger.error(
                "Two-factor authentication required. "
                "For test servers, this should not happen. "
                "Please disable 2FA in test account or provide password via environment."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False

    def _sanitize_channel_name(self, channel_name: str) -> str:
        """Sanitize channel name for filesystem use."""
        # Remove invalid filesystem characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = ''.join(c if c not in invalid_chars else '_' for c in channel_name)
        return sanitized.strip()

    def _get_message_path(self, channel_name: str, date: datetime) -> Path:
        """
        Get the file path for storing messages based on date partition.
        Format: data/raw/telegram_messages/YYYY-MM-DD/channel_name.json
        """
        date_str = date.strftime('%Y-%m-%d')
        sanitized_channel = self._sanitize_channel_name(channel_name)
        date_dir = self.data_messages_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / f"{sanitized_channel}.json"

    def _get_image_path(self, channel_name: str, message_id: int) -> Path:
        """
        Get the file path for storing an image.
        Format: data/raw/images/channel_name/message_id.jpg
        """
        sanitized_channel = self._sanitize_channel_name(channel_name)
        channel_dir = self.data_images_dir / sanitized_channel
        channel_dir.mkdir(parents=True, exist_ok=True)
        return channel_dir / f"{message_id}.jpg"

    async def _download_image(self, message, channel_name: str) -> Optional[str]:
        """
        Download image from message media if available.
        Returns relative path to image if successful, None otherwise.
        """
        try:
            if not message.media:
                return None

            # Check if media is a photo
            if isinstance(message.media, MessageMediaPhoto):
                image_path = self._get_image_path(channel_name, message.id)
                
                # Skip if already downloaded (idempotency)
                if image_path.exists():
                    logger.debug(f"Image already exists: {image_path}")
                    return str(image_path.relative_to(Path.cwd()))

                # Download the photo
                await self.client.download_media(message, file=str(image_path))
                logger.info(f"Downloaded image: {image_path}")
                return str(image_path.relative_to(Path.cwd()))

            # Check if media is a document with image mime type
            elif isinstance(message.media, MessageMediaDocument):
                if message.media.document.mime_type and message.media.document.mime_type.startswith('image/'):
                    image_path = self._get_image_path(channel_name, message.id)
                    
                    if image_path.exists():
                        logger.debug(f"Image already exists: {image_path}")
                        return str(image_path.relative_to(Path.cwd()))

                    await self.client.download_media(message, file=str(image_path))
                    logger.info(f"Downloaded image: {image_path}")
                    return str(image_path.relative_to(Path.cwd()))

        except Exception as e:
            logger.warning(f"Failed to download image for message {message.id}: {e}")
            return None

        return None

    def _message_to_dict(self, message, channel_name: str, image_path: Optional[str]) -> Dict:
        """
        Convert Telegram message to dictionary with required fields.
        Preserves original API structure for raw data lake.
        """
        return {
            'message_id': message.id,
            'channel_name': channel_name,
            'message_date': message.date.isoformat() if message.date else None,
            'message_text': message.text or '',
            'views': getattr(message, 'views', None),
            'forwards': getattr(message, 'forwards', None),
            'has_media': message.media is not None,
            'image_path': image_path,
            # Preserve original API structure
            '_raw': {
                'id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'message': message.text,
                'views': getattr(message, 'views', None),
                'forwards': getattr(message, 'forwards', None),
                'media': bool(message.media),
                'entities': [str(e) for e in (message.entities or [])],
            }
        }

    async def _load_existing_messages(self, file_path: Path) -> Dict[int, Dict]:
        """Load existing messages from JSON file (for idempotency)."""
        if not file_path.exists():
            return {}

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                # Convert list to dict keyed by message_id
                if isinstance(data, list):
                    return {msg['message_id']: msg for msg in data}
                return {}
        except Exception as e:
            logger.warning(f"Failed to load existing messages from {file_path}: {e}")
            return {}

    async def _save_messages(self, file_path: Path, messages: List[Dict]):
        """Save messages to JSON file atomically."""
        try:
            # Sort by message_id for consistency
            messages_sorted = sorted(messages, key=lambda x: x['message_id'])
            
            # Write atomically
            temp_path = file_path.with_suffix('.json.tmp')
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(messages_sorted, indent=2, ensure_ascii=False))
            
            # Atomic rename
            temp_path.replace(file_path)
            logger.info(f"Saved {len(messages)} messages to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save messages to {file_path}: {e}")
            raise

    async def scrape_channel(self, channel_name: str) -> Dict:
        """
        Scrape messages from a Telegram channel.
        Returns statistics about the scraping operation.
        """
        stats = {
            'channel': channel_name,
            'total_messages': 0,
            'new_messages': 0,
            'images_downloaded': 0,
            'errors': 0,
            'start_time': datetime.now().isoformat(),
        }

        try:
            logger.info(f"Starting scrape for channel: {channel_name}")

            # Get entity (channel/user)
            entity = await self.client.get_entity(channel_name)
            logger.info(f"Found entity: {entity.id} - {channel_name}")

            # Group messages by date for partitioning
            messages_by_date: Dict[str, Dict[int, Dict]] = {}

            # Scrape messages in batches
            total_fetched = 0
            async for message in self.client.iter_messages(entity, limit=MAX_MESSAGES):
                try:
                    # Get date partition
                    message_date = message.date.date() if message.date else datetime.now().date()
                    date_key = message_date.strftime('%Y-%m-%d')
                    
                    # Initialize date bucket if needed
                    if date_key not in messages_by_date:
                        messages_by_date[date_key] = {}

                    # Skip if already processed (idempotency check will happen on save)
                    total_fetched += 1

                    # Download image if available
                    image_path = None
                    if message.media:
                        image_path = await self._download_image(message, channel_name)
                        if image_path:
                            stats['images_downloaded'] += 1

                    # Convert to dict
                    msg_dict = self._message_to_dict(message, channel_name, image_path)
                    
                    # Store by date and message_id
                    messages_by_date[date_key][message.id] = msg_dict

                    # Log progress
                    if total_fetched % BATCH_SIZE == 0:
                        logger.info(f"Processed {total_fetched} messages from {channel_name}")

                except Exception as e:
                    logger.error(f"Error processing message {message.id} from {channel_name}: {e}")
                    stats['errors'] += 1
                    continue

            # Save messages partitioned by date
            for date_key, messages_dict in messages_by_date.items():
                file_path = self._get_message_path(channel_name, datetime.strptime(date_key, '%Y-%m-%d').date())
                
                # Load existing messages for idempotency
                existing = await self._load_existing_messages(file_path)
                
                # Merge: new messages override existing ones
                existing.update(messages_dict)
                merged_messages = list(existing.values())
                
                # Count new messages
                new_count = len(messages_dict)
                
                # Save
                await self._save_messages(file_path, merged_messages)
                
                stats['new_messages'] += new_count
                stats['total_messages'] = len(merged_messages)

            stats['end_time'] = datetime.now().isoformat()
            logger.info(f"Completed scrape for {channel_name}: {stats}")
            return stats

        except errors.UsernameNotOccupiedError:
            logger.error(f"Channel not found: {channel_name}")
            stats['errors'] += 1
            stats['error_message'] = f"Channel not found: {channel_name}"
            return stats
        except errors.FloodWaitError as e:
            logger.error(f"Rate limit exceeded for {channel_name}. Wait {e.seconds} seconds.")
            stats['errors'] += 1
            stats['error_message'] = f"Rate limit: wait {e.seconds} seconds"
            return stats
        except Exception as e:
            logger.error(f"Unexpected error scraping {channel_name}: {e}", exc_info=True)
            stats['errors'] += 1
            stats['error_message'] = str(e)
            return stats

    async def scrape_all_channels(self) -> Dict:
        """
        Scrape all configured channels and return aggregate statistics.
        """
        logger.info(f"Starting scrape for {len(CHANNELS)} channels: {CHANNELS}")
        
        all_stats = {
            'total_channels': len(CHANNELS),
            'channels': [],
            'start_time': datetime.now().isoformat(),
        }

        for channel in CHANNELS:
            stats = await self.scrape_channel(channel)
            all_stats['channels'].append(stats)
            
            # Small delay between channels to avoid rate limits
            await asyncio.sleep(2)

        all_stats['end_time'] = datetime.now().isoformat()
        all_stats['total_messages'] = sum(s.get('total_messages', 0) for s in all_stats['channels'])
        all_stats['total_images'] = sum(s.get('images_downloaded', 0) for s in all_stats['channels'])
        all_stats['total_errors'] = sum(s.get('errors', 0) for s in all_stats['channels'])

        logger.info(f"Scraping complete. Total messages: {all_stats['total_messages']}, "
                   f"Total images: {all_stats['total_images']}, Errors: {all_stats['total_errors']}")

        # Save summary statistics
        summary_path = Path(LOG_DIR) / f"scrape_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(all_stats, indent=2, ensure_ascii=False))
        
        logger.info(f"Summary saved to {summary_path}")
        return all_stats

    async def close(self):
        """Close Telegram client connection."""
        await self.client.disconnect()
        logger.info("Disconnected from Telegram")


async def run_dry_run():
    """Run pipeline without Telegram: write sample data lake files and logs."""
    logger.info("DRY RUN: Skipping Telegram, writing sample data to validate pipeline")
    data_messages = Path(DATA_RAW_MESSAGES)
    data_images = Path(DATA_RAW_IMAGES)
    data_messages.mkdir(parents=True, exist_ok=True)
    data_images.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    sample = [
        {"message_id": 1, "channel_name": "CheMed", "message_date": f"{today}T12:00:00",
         "message_text": "[DRY RUN] Sample message", "views": 100, "forwards": 5,
         "has_media": False, "image_path": None, "_raw": {}},
    ]
    for ch in CHANNELS[:1]:
        sanitized = ''.join(c if c not in '<>:"/\\|?*' else '_' for c in ch).strip()
        path = data_messages / today / f"{sanitized}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(sample, indent=2, ensure_ascii=False))
        logger.info(f"DRY RUN: Wrote {path}")
    summary_path = Path(LOG_DIR) / f"scrape_summary_dryrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary = {"dry_run": True, "channels": CHANNELS[:1], "sample_files": 1}
    async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(summary, indent=2))
    logger.info(f"DRY RUN: Summary {summary_path}")
    logger.info("DRY RUN: Pipeline test completed successfully")


async def main():
    """Main entry point for the scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram Channel Scraper")
    parser.add_argument('--dry-run', action='store_true', help='Run pipeline without connecting to Telegram, generating sample data.')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Medical Telegram Warehouse - Task-1: Data Scraping & Collection")
    logger.info("=" * 80)

    if DRY_RUN or args.dry_run:
        await run_dry_run()
        return

    scraper = TelegramScraper()
    
    try:
        connected = await scraper.connect()
        if not connected:
            logger.error("Failed to establish Telegram connection. Exiting.")
            return

        stats = await scraper.scrape_all_channels()
        
        logger.info("=" * 80)
        logger.info("Scraping Pipeline Completed Successfully")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in scraping pipeline: {e}", exc_info=True)
        raise
    finally:
        if not DRY_RUN:
            await scraper.close()


if __name__ == '__main__':
    asyncio.run(main())

