"""
Load Raw Telegram JSON Data into PostgreSQL
Task-2: Data Modeling & Transformation - Raw Data Loading

This script reads JSON files from the raw data lake and loads them
into PostgreSQL raw.telegram_messages table.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values, Json
from psycopg2.sql import SQL, Identifier
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
DATA_RAW_MESSAGES = Path(os.getenv('DATA_RAW_MESSAGES', 'data/raw/telegram_messages'))

# PostgreSQL connection parameters
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5433')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'medical_warehouse')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'medical_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'medical_pass')

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class RawDataLoader:
    """Load raw Telegram JSON data into PostgreSQL raw schema."""

    def __init__(self):
        """Initialize the data loader."""
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish connection to PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to PostgreSQL: {POSTGRES_DB}@{POSTGRES_HOST}:{POSTGRES_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def create_raw_schema(self):
        """Create raw schema and telegram_messages table if they don't exist."""
        try:
            # Create raw schema
            self.cursor.execute("CREATE SCHEMA IF NOT EXISTS raw;")
            logger.info("Schema 'raw' created or already exists")

            # Create raw.telegram_messages table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS raw.telegram_messages (
                message_id BIGINT NOT NULL,
                channel_name VARCHAR(255) NOT NULL,
                message_date TIMESTAMP,
                message_text TEXT,
                views INTEGER,
                forwards INTEGER,
                has_media BOOLEAN DEFAULT FALSE,
                image_path VARCHAR(500),
                raw_data JSONB,
                loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (message_id, channel_name)
            );
            """

            self.cursor.execute(create_table_sql)

            # Create indexes for better query performance
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_telegram_messages_channel ON raw.telegram_messages(channel_name);",
                "CREATE INDEX IF NOT EXISTS idx_telegram_messages_date ON raw.telegram_messages(message_date);",
                "CREATE INDEX IF NOT EXISTS idx_telegram_messages_loaded_at ON raw.telegram_messages(loaded_at);",
                "CREATE INDEX IF NOT EXISTS idx_telegram_messages_raw_data ON raw.telegram_messages USING GIN(raw_data);"
            ]

            for index_sql in index_sqls:
                self.cursor.execute(index_sql)

            self.conn.commit()
            logger.info("Table raw.telegram_messages created or already exists with indexes")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to create schema/table: {e}")
            raise

    def load_json_file(self, file_path: Path) -> int:
        """
        Load messages from a single JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Number of messages loaded/updated
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)

            if not isinstance(messages, list):
                logger.warning(f"File {file_path} does not contain a JSON array, skipping")
                return 0

            logger.info(f"Loading {len(messages)} messages from {file_path.name}")

            loaded_count = 0

            for msg in messages:
                try:
                    # Prepare data for insert/update (upsert)
                    upsert_sql = """
                    INSERT INTO raw.telegram_messages
                        (message_id, channel_name, message_date, message_text, views,
                         forwards, has_media, image_path, raw_data, loaded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (message_id, channel_name)
                    DO UPDATE SET
                        message_date = EXCLUDED.message_date,
                        message_text = EXCLUDED.message_text,
                        views = EXCLUDED.views,
                        forwards = EXCLUDED.forwards,
                        has_media = EXCLUDED.has_media,
                        image_path = EXCLUDED.image_path,
                        raw_data = EXCLUDED.raw_data,
                        loaded_at = CURRENT_TIMESTAMP;
                    """

                    # Parse message_date
                    message_date = None
                    if msg.get('message_date'):
                        try:
                            message_date = datetime.fromisoformat(msg['message_date'].replace('Z', '+00:00'))
                        except Exception as e:
                            logger.debug(f"Could not parse message_date {msg.get('message_date')}: {e}")

                    self.cursor.execute(upsert_sql, (
                        msg.get('message_id'),
                        msg.get('channel_name'),
                        message_date,
                        msg.get('message_text') or '',
                        msg.get('views'),
                        msg.get('forwards'),
                        msg.get('has_media', False),
                        msg.get('image_path'),
                        Json(msg)  # Store entire message as JSONB for audit/backup
                    ))
                    loaded_count += 1

                except Exception as e:
                    logger.warning(f"Failed to load message {msg.get('message_id')} from {file_path.name}: {e}")
                    continue

            self.conn.commit()
            logger.info(f"Successfully loaded {loaded_count} messages from {file_path.name}")
            return loaded_count

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {file_path}: {e}")
            return 0
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error loading file {file_path}: {e}")
            return 0

    def load_all_raw_files(self) -> Dict[str, int]:
        """
        Load all JSON files from data/raw/telegram_messages directory.

        Returns:
            Dictionary with loading statistics
        """
        if not DATA_RAW_MESSAGES.exists():
            logger.error(f"Raw messages directory does not exist: {DATA_RAW_MESSAGES}")
            return {}

        stats = {
            'files_processed': 0,
            'messages_loaded': 0,
            'errors': 0
        }

        # Find all JSON files recursively
        json_files = list(DATA_RAW_MESSAGES.rglob('*.json'))
        logger.info(f"Found {len(json_files)} JSON files to process")

        for json_file in json_files:
            try:
                messages_loaded = self.load_json_file(json_file)
                stats['files_processed'] += 1
                stats['messages_loaded'] += messages_loaded
            except Exception as e:
                logger.error(f"Error processing file {json_file}: {e}")
                stats['errors'] += 1

        return stats

    def get_table_stats(self) -> Dict[str, int]:
        """Get statistics from raw.telegram_messages table."""
        try:
            self.cursor.execute("""
                SELECT
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT channel_name) as unique_channels,
                    MIN(message_date) as earliest_message,
                    MAX(message_date) as latest_message
                FROM raw.telegram_messages;
            """)

            result = self.cursor.fetchone()
            return {
                'total_messages': result[0] or 0,
                'unique_channels': result[1] or 0,
                'earliest_message': result[2],
                'latest_message': result[3]
            }
        except Exception as e:
            logger.error(f"Error getting table stats: {e}")
            return {}

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")


def main():
    """Main execution function."""
    logger.info("Starting raw data loading process...")

    loader = RawDataLoader()

    try:
        # Connect to database
        if not loader.connect():
            logger.error("Failed to connect to PostgreSQL. Exiting.")
            sys.exit(1)

        # Create schema and table
        loader.create_raw_schema()

        # Load all JSON files
        stats = loader.load_all_raw_files()

        # Print statistics
        logger.info("=" * 60)
        logger.info("Loading Statistics:")
        logger.info(f"  Files processed: {stats.get('files_processed', 0)}")
        logger.info(f"  Messages loaded: {stats.get('messages_loaded', 0)}")
        logger.info(f"  Errors: {stats.get('errors', 0)}")

        # Get table statistics
        table_stats = loader.get_table_stats()
        logger.info("\nTable Statistics:")
        logger.info(f"  Total messages in database: {table_stats.get('total_messages', 0)}")
        logger.info(f"  Unique channels: {table_stats.get('unique_channels', 0)}")
        logger.info(f"  Earliest message: {table_stats.get('earliest_message')}")
        logger.info(f"  Latest message: {table_stats.get('latest_message')}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        loader.close()


if __name__ == '__main__':
    main()
