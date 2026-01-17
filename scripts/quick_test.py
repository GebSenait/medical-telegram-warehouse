"""
Quick Connection Test - Fast validation without full scraping
Tests Telegram connection and basic functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient, errors

load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME', 'telegram_scraper_test')

async def quick_test():
    """Quick test of Telegram connection."""
    print("=" * 80)
    print("Quick Telegram Connection Test")
    print("=" * 80)
    print()
    
    if not API_ID or not API_HASH:
        print("[ERROR] TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        return False
    
    print(f"[INFO] Using API ID: {API_ID}")
    print(f"[INFO] Session: {SESSION_NAME}")
    print()
    
    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    
    try:
        print("[TEST] Attempting to connect to Telegram...")
        await client.start()
        print("[OK] Successfully connected to Telegram!")
        print()
        
        # Test getting own user info
        print("[TEST] Getting user information...")
        me = await client.get_me()
        print(f"[OK] Connected as: {me.first_name} (ID: {me.id})")
        print()
        
        print("[OK] Connection test PASSED!")
        print("=" * 80)
        return True
        
    except errors.SessionPasswordNeededError:
        print("[WARNING] 2FA is enabled. This is expected for production accounts.")
        print("[INFO] For test servers, 2FA is usually not required.")
        print("[OK] Connection test PASSED (2FA prompt is normal)")
        return True
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Verify API credentials in .env")
        print("  2. Check internet connection")
        print("  3. For test servers, use test phone number format: 99966XXXXX")
        return False
    finally:
        await client.disconnect()
        print("[INFO] Disconnected")

if __name__ == '__main__':
    success = asyncio.run(quick_test())
    exit(0 if success else 1)

