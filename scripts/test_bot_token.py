"""
Test Bot Token - Validates bot token and runs scraper
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient, errors

load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def test_bot_token():
    """Test bot token authentication."""
    print("=" * 80)
    print("Bot Token Test")
    print("=" * 80)
    print()
    
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        print("[ERROR] TELEGRAM_BOT_TOKEN not set in .env")
        print()
        print("To get bot token:")
        print("  1. Open Telegram")
        print("  2. Search: @BotFather")
        print("  3. Send: /newbot")
        print("  4. Copy the token")
        print("  5. Add to .env: TELEGRAM_BOT_TOKEN=your_token")
        return False
    
    if not API_ID or not API_HASH:
        print("[ERROR] TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")
        print("Get from: https://my.telegram.org/apps")
        return False
    
    if API_ID == '17349':
        print("[WARNING] Using test server API (17349)")
        print("Bot tokens require PRODUCTION API credentials")
        print("Get production API from: https://my.telegram.org/apps")
        return False
    
    print(f"[INFO] Testing bot token: {BOT_TOKEN[:20]}...")
    print()
    
    client = TelegramClient('bot_test', int(API_ID), API_HASH)
    
    try:
        print("[TEST] Connecting with bot token...")
        await client.start(bot_token=BOT_TOKEN)
        print("[OK] Successfully authenticated with bot token!")
        print()
        
        me = await client.get_me()
        print(f"[OK] Bot info:")
        print(f"  Username: @{me.username}")
        print(f"  ID: {me.id}")
        print(f"  First Name: {me.first_name}")
        print()
        
        print("[OK] Bot token is valid and working!")
        print("You can now run the scraper without phone or code:")
        print("  .\\venv\\Scripts\\python.exe -m src.scraper")
        print()
        
        return True
        
    except errors.AuthKeyUnregisteredError:
        print("[ERROR] Invalid bot token")
        print("Verify the token is correct from @BotFather")
        return False
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False
    finally:
        await client.disconnect()

if __name__ == '__main__':
    success = asyncio.run(test_bot_token())
    sys.exit(0 if success else 1)

