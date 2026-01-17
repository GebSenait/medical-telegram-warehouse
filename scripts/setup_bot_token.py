"""
Bot Token Setup Helper
Guides you through setting up bot token authentication
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_env_file():
    """Check and update .env file."""
    env_path = Path('.env')
    if not env_path.exists():
        print("[ERROR] .env file not found!")
        return False
    
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    print("\n" + "=" * 80)
    print("Bot Token Setup Status")
    print("=" * 80)
    print()
    
    # Check API credentials
    if api_id and api_id != 'your_api_id_here' and api_id != '17349':
        print(f"[OK] Production API ID: {api_id}")
    elif api_id == '17349':
        print("[WARNING] Using test server API ID (17349)")
        print("  Bot tokens require PRODUCTION API credentials")
        print("  Get production API from: https://my.telegram.org/apps")
    else:
        print("[MISSING] TELEGRAM_API_ID not configured")
    
    if api_hash and api_hash != 'your_api_hash_here':
        print(f"[OK] API Hash configured: {api_hash[:10]}...")
    else:
        print("[MISSING] TELEGRAM_API_HASH not configured")
    
    # Check bot token
    if bot_token and bot_token != 'your_bot_token_here':
        print(f"[OK] Bot Token configured: {bot_token[:20]}...")
        return True
    else:
        print("[MISSING] TELEGRAM_BOT_TOKEN not configured")
        print()
        print("To get bot token:")
        print("  1. Open Telegram")
        print("  2. Search for @BotFather")
        print("  3. Send: /newbot")
        print("  4. Follow prompts")
        print("  5. Copy the token")
        print("  6. Add to .env: TELEGRAM_BOT_TOKEN=your_token_here")
        return False

def update_env_template():
    """Update ENV_TEMPLATE.txt with bot token option."""
    template = """# Telegram API Credentials
# Option 1: Production API (for bot token - recommended)
TELEGRAM_API_ID=your_production_api_id_here
TELEGRAM_API_HASH=your_production_api_hash_here

# Option 2: Test Server (for development)
# TELEGRAM_API_ID=17349
# TELEGRAM_API_HASH=344583e45741c457fe1862106095a5eb

# Bot Token (from @BotFather) - No phone/code needed!
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Session Configuration
TELEGRAM_SESSION_NAME=telegram_scraper

# Channels to scrape (comma-separated)
TELEGRAM_CHANNELS=CheMed,Lobelia Cosmetics,Tikvah Pharma

# Scraping Configuration
MAX_MESSAGES_PER_CHANNEL=1000
SCRAPER_BATCH_SIZE=100

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Data Lake Paths
DATA_RAW_MESSAGES=data/raw/telegram_messages
DATA_RAW_IMAGES=data/raw/images
"""
    with open('ENV_TEMPLATE.txt', 'w') as f:
        f.write(template)
    print("[OK] Updated ENV_TEMPLATE.txt with bot token option")

def main():
    """Main setup helper."""
    print("=" * 80)
    print("Bot Token Setup Helper")
    print("=" * 80)
    print()
    
    has_bot_token = check_env_file()
    
    if not has_bot_token:
        print()
        print("=" * 80)
        print("Next Steps:")
        print("=" * 80)
        print()
        print("1. Get Production API Credentials:")
        print("   - Visit: https://my.telegram.org/apps")
        print("   - Log in with your phone number")
        print("   - Create application")
        print("   - Copy api_id and api_hash")
        print()
        print("2. Create Bot:")
        print("   - Open Telegram")
        print("   - Search: @BotFather")
        print("   - Send: /newbot")
        print("   - Follow prompts")
        print("   - Copy bot token")
        print()
        print("3. Update .env file:")
        print("   - Add production API_ID and API_HASH")
        print("   - Add TELEGRAM_BOT_TOKEN=your_token")
        print("   - Remove test server credentials")
        print()
        print("4. Run scraper:")
        print("   .\\venv\\Scripts\\python.exe -m src.scraper")
        print()
    else:
        print()
        print("[OK] Bot token is configured!")
        print("You can now run: .\\venv\\Scripts\\python.exe -m src.scraper")
        print("No phone or verification code needed!")
        print()
    
    update_env_template()

if __name__ == '__main__':
    main()

