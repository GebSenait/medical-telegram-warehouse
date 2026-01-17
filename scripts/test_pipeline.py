"""
Pipeline Validation Script
Tests the configuration and setup without requiring actual Telegram credentials.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_environment_setup():
    """Test environment configuration."""
    print("=" * 80)
    print("Pipeline Validation - Task-1: Data Scraping & Collection")
    print("=" * 80)
    print()
    
    # Load .env
    load_dotenv()
    
    # Check .env file exists
    env_path = Path('.env')
    if not env_path.exists():
        print("[ERROR] .env file not found!")
        print("   Please create .env file from ENV_TEMPLATE.txt")
        return False
    print("[OK] .env file exists")
    
    # Check required environment variables
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or api_id == 'your_api_id_here':
        print("[WARNING] TELEGRAM_API_ID not configured (using placeholder)")
        print("   Please set TELEGRAM_API_ID in .env file")
    else:
        print(f"[OK] TELEGRAM_API_ID configured: {api_id[:5]}...")
    
    if not api_hash or api_hash == 'your_api_hash_here':
        print("[WARNING] TELEGRAM_API_HASH not configured (using placeholder)")
        print("   Please set TELEGRAM_API_HASH in .env file")
    else:
        print(f"[OK] TELEGRAM_API_HASH configured: {api_hash[:5]}...")
    
    channels = os.getenv('TELEGRAM_CHANNELS', '')
    print(f"[OK] Channels configured: {channels}")
    
    print()
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor >= 11:
        print(f"[OK] Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"[WARNING] Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        print("   Recommended: Python 3.11+")
    
    print()
    
    # Check required packages
    print("Checking dependencies...")
    required_packages = {
        'telethon': ('telethon', 'Telegram API client'),
        'aiofiles': ('aiofiles', 'Async file I/O'),
        'python-dotenv': ('dotenv', 'Environment variable management'),
        'python-dateutil': ('dateutil', 'Date utilities'),
        'aiohttp': ('aiohttp', 'Async HTTP client')
    }
    
    missing_packages = []
    for package_name, (import_name, description) in required_packages.items():
        try:
            __import__(import_name)
            print(f"  [OK] {package_name} - {description}")
        except ImportError:
            print(f"  [ERROR] {package_name} - {description} - NOT INSTALLED")
            missing_packages.append(package_name)
    
    if missing_packages:
        print()
        print("[ERROR] Missing packages. Install with:")
        print("   pip install -r requirements.txt")
        return False
    
    print()
    print("[OK] All dependencies installed")
    print()
    
    # Check directory structure
    print("Checking directory structure...")
    required_dirs = [
        'src',
        'data/raw/telegram_messages',
        'data/raw/images',
        'logs'
    ]
    
    all_dirs_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  [OK] {dir_path}/")
        else:
            print(f"  [ERROR] {dir_path}/ - MISSING")
            all_dirs_exist = False
    
    if not all_dirs_exist:
        print()
        print("Creating missing directories...")
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"  [CREATED] {dir_path}/")
    
    print()
    
    # Check source files
    print("Checking source files...")
    if Path('src/scraper.py').exists():
        print("  [OK] src/scraper.py")
    else:
        print("  [ERROR] src/scraper.py - MISSING")
        return False
    
    print()
    print("=" * 80)
    
    # Final validation
    if missing_packages:
        print("[FAILED] VALIDATION FAILED: Install missing packages first")
        print()
        print("Next steps:")
        print("  1. pip install -r requirements.txt")
        print("  2. Run this script again")
        return False
    
    if not api_id or api_id == 'your_api_id_here' or not api_hash or api_hash == 'your_api_hash_here':
        print("[INCOMPLETE] VALIDATION INCOMPLETE: Configure Telegram credentials")
        print()
        print("Next steps:")
        print("  1. Get credentials from https://my.telegram.org/apps")
        print("  2. Update TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")
        print("  3. Run: python -m src.scraper")
        return False
    
    print("[PASSED] VALIDATION PASSED: Ready to run scraper!")
    print()
    print("To run the scraper:")
    print("  python -m src.scraper")
    print("  OR")
    print("  docker-compose up")
    print("=" * 80)
    return True

if __name__ == '__main__':
    success = test_environment_setup()
    sys.exit(0 if success else 1)

