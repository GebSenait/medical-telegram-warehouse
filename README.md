# Medical Telegram Warehouse - Task-1: Data Scraping & Collection

**Enterprise-Grade ELT Pipeline for Ethiopian Medical/Pharmaceutical Telegram Channel Data**

## 🎯 Business Understanding

This project extracts insights from public Ethiopian medical and pharmaceutical Telegram channels, applying fintech fraud detection principles (anomaly detection, volume spikes, behavior patterns) to the medical/pharmaceutical domain.

### Architecture Overview

```
┌─────────────────┐
│  Telegram API   │
└────────┬────────┘
         │
         │ Extract
         ▼
┌─────────────────┐
│  Raw Data Lake  │ ◄── Task-1
└────────┬────────┘
         │
         │ Transform
         ▼
┌─────────────────┐
│   dbt Layer     │ ◄── Future Task
└────────┬────────┘
         │
         │ Enrich
         ▼
┌─────────────────┐
│   YOLO Layer    │ ◄── Future Task
└────────┬────────┘
         │
         │ Expose
         ▼
┌─────────────────┐
│   FastAPI       │ ◄── Future Task
└─────────────────┘
```

**Task-1**: Extract raw Telegram data and load into the raw data lake. This is the foundation that all downstream analytics depend on.

---

## 📋 Git Initialization & Branching

✅ **Completed**
- Repository initialized
- `main` branch created
- `task-1-dev` branch created and active

```bash
git status  # Should show task-1-dev branch
```

---

## 🏗️ Project Structure

```
medical-telegram-warehouse/
├── .gitignore                 # Git ignore rules
├── .env                       # Environment variables 
├── .env.example              # Template for .env file
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose configuration
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── src/
│   ├── __init__.py
│   └── scraper.py            # Production-ready scraper
│
├── data/
│   └── raw/
│       ├── telegram_messages/    # Message JSON files
│       │   └── YYYY-MM-DD/
│       │       └── channel_name.json
│       └── images/               # Downloaded images
│           └── channel_name/
│               └── message_id.jpg
│
└── logs/
    ├── scraper_YYYYMMDD_HHMMSS.log
    └── scrape_summary_YYYYMMDD_HHMMSS.json
```

---

## 🔐 Telegram Access Setup

### Environment Variables

1. **Copy the example environment file:**
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   
   # Linux/Mac
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```env
   TELEGRAM_API_ID=your_api_id_here
   TELEGRAM_API_HASH=your_api_hash_here
   TELEGRAM_SESSION_NAME=telegram_scraper
   TELEGRAM_CHANNELS=CheMed,Lobelia Cosmetics,Tikvah Pharma
   MAX_MESSAGES_PER_CHANNEL=1000
   SCRAPER_BATCH_SIZE=100
   LOG_LEVEL=INFO
   ```

### Getting Telegram API Credentials

1. Visit [https://my.telegram.org/apps](https://my.telegram.org/apps)
2. Log in with your phone number
3. Create a new application
4. Copy `api_id` and `api_hash` to `.env`

**⚠️ Important:**
- Use **sandbox/test credentials** for development
- `.env` is **NEVER committed** (already in `.gitignore`)
- For production, use environment variables or secrets management

### Authentication Flow

The scraper uses Telethon's session-based authentication:
- First run: Requires phone number and verification code
- Subsequent runs: Uses saved session file (`.session`)
- Session files are **not committed** to Git

**If 2FA is enabled:**
- The scraper will prompt for password
- For sandbox accounts, disable 2FA for easier testing

---

## 🚀 Scraper Design

### Key Features

✅ **Idempotent Operations**: Safe to re-run without duplicating data  
✅ **Date Partitioning**: Messages stored by date for efficient querying  
✅ **Image Download**: Automatic image extraction and storage  
✅ **Error Handling**: Graceful handling of rate limits, network errors  
✅ **Logging**: Comprehensive logging for debugging and monitoring  
✅ **Non-blocking I/O**: Async operations for performance  

### Data Extraction Schema

Each message is extracted with the following fields:

```json
{
  "message_id": 12345,
  "channel_name": "CheMed",
  "message_date": "2024-01-15T10:30:00",
  "message_text": "Message content here",
  "views": 1000,
  "forwards": 50,
  "has_media": true,
  "image_path": "data/raw/images/CheMed/12345.jpg",
  "_raw": {
    // Original API response preserved
  }
}
```

### Supported Channels

**Default Channels:**
- CheMed
- Lobelia Cosmetics
- Tikvah Pharma

**Additional Channels:**
- Add more channels from [https://et.tgstat.com/medicine](https://et.tgstat.com/medicine)
- Configure via `TELEGRAM_CHANNELS` in `.env` (comma-separated)

---

## 🗄️ Data Lake Implementation

### Message Storage

**Path Pattern:** `data/raw/telegram_messages/YYYY-MM-DD/channel_name.json`

**Example:**
```
data/raw/telegram_messages/2024-01-15/CheMed.json
```

**File Format:**
- JSON array of message objects
- Sorted by `message_id`
- Idempotent: Re-running appends/updates messages

### Image Storage

**Path Pattern:** `data/raw/images/channel_name/message_id.jpg`

**Example:**
```
data/raw/images/CheMed/12345.jpg
```

**Features:**
- Only downloads images (photos)
- Skips duplicates (idempotent)
- Preserves original file format

---

## 📊 Logging & Error Handling

### Log Files

**Location:** `logs/`

**Files Generated:**
1. `scraper_YYYYMMDD_HHMMSS.log` - Detailed execution logs
2. `scrape_summary_YYYYMMDD_HHMMSS.json` - Summary statistics

### Log Levels

- **INFO**: Normal operations, progress updates
- **WARNING**: Recoverable errors (missing images, etc.)
- **ERROR**: Critical errors (channel not found, rate limits)
- **DEBUG**: Detailed debugging information

### Error Handling

✅ **Rate Limits**: Automatically waits when FloodWaitError occurs  
✅ **Network Errors**: Retries with exponential backoff  
✅ **Missing Channels**: Logs error and continues with other channels  
✅ **Image Download Failures**: Logs warning but continues processing  

---

## 🐳 Execution Instructions

### Option 1: Docker (Recommended)

**Prerequisites:**
- Docker Desktop installed
- `.env` file configured

**Build and Run:**
```bash
# Build Docker image
docker-compose build

# Run scraper
docker-compose up
```

**Run in Background:**
```bash
docker-compose up -d
```

**View Logs:**
```bash
docker-compose logs -f telegram-scraper
```

**Stop:**
```bash
docker-compose down
```

### Option 2: Local Python

**Prerequisites:**
- Python 3.11
- `.env` file configured

**Setup:**
```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Run:**
```bash
python -m src.scraper
```

### First Run Authentication

On first run, Telethon will prompt:
1. **Phone number**: Enter your Telegram phone number (with country code, e.g., +251...)
2. **Verification code**: Enter code sent via Telegram
3. **Password (if 2FA enabled)**: Enter your 2FA password

**Subsequent runs:** Uses saved session

---

## ✅ Validation Checklist

Before considering Task-1 complete, verify:

### 1. Git Setup
- [x] Repository initialized
- [x] `main` branch exists
- [x] `task-1-dev` branch exists and active
- [x] `.gitignore` configured (`.env` ignored)
- [ ] Initial commit made (ready for commit)

### 2. Environment Configuration
- [ ] `.env` file created from `.env.example`
- [ ] `TELEGRAM_API_ID` set (mock/sandbox credentials OK)
- [ ] `TELEGRAM_API_HASH` set
- [ ] `TELEGRAM_CHANNELS` configured

### 3. Data Extraction
- [ ] Scraper runs without errors
- [ ] Messages extracted from at least one channel
- [ ] JSON files created in `data/raw/telegram_messages/YYYY-MM-DD/`
- [ ] Message files contain valid JSON with required fields
- [ ] Images downloaded to `data/raw/images/channel_name/`

### 4. Data Lake Structure
- [ ] Directory structure matches specification:
  - `data/raw/telegram_messages/YYYY-MM-DD/channel_name.json`
  - `data/raw/images/channel_name/message_id.jpg`
- [ ] Files are properly partitioned by date
- [ ] Channel names are sanitized for filesystem

### 5. Logging
- [ ] Log files created in `logs/` directory
- [ ] Logs contain channel scraping information
- [ ] Error logs exist (if any errors occurred)
- [ ] Summary JSON file generated

### 6. Idempotency
- [ ] Re-running scraper doesn't duplicate messages
- [ ] Re-running scraper doesn't re-download existing images
- [ ] Existing messages are updated if re-scraped

### 7. Docker Execution
- [ ] Docker image builds successfully
- [ ] Container runs and completes scraping
- [ ] Data persists to host filesystem via volumes

### 8. Code Quality
- [ ] No linter errors
- [ ] Code follows production best practices
- [ ] Error handling implemented
- [ ] Type hints and docstrings present

---

## 🔍 Testing the Pipeline

### Quick Test

```bash
# Set minimal message limit for testing
export MAX_MESSAGES_PER_CHANNEL=10

# Run scraper
python -m src.scraper

# Verify output
ls -R data/raw/
ls logs/
```

### Verify JSON Structure

```bash
# Check message file
cat data/raw/telegram_messages/$(date +%Y-%m-%d)/CheMed.json | jq '.[0]'

# Verify required fields exist
cat data/raw/telegram_messages/$(date +%Y-%m-%d)/CheMed.json | jq '.[0] | keys'
```

### Verify Images

```bash
# Check images downloaded
ls -lh data/raw/images/CheMed/

# Verify image files are valid
file data/raw/images/CheMed/*.jpg
```

---

## 📈 Performance Considerations

- **Batch Processing**: Messages processed in batches (configurable via `SCRAPER_BATCH_SIZE`)
- **Async I/O**: Non-blocking operations for network and file I/O
- **Rate Limiting**: Respects Telegram API rate limits automatically
- **Idempotency**: Safe to re-run for incremental updates

**Expected Performance:**
- ~100-500 messages/second (depends on network and rate limits)
- Image downloads: ~5-10 images/second

---

## 🚨 Troubleshooting

### Issue: "SessionPasswordNeededError"

**Solution**: Your account has 2FA enabled. Either:
1. Disable 2FA in Telegram settings (for sandbox accounts)
2. Enter password when prompted
3. Use a test account without 2FA

### Issue: "UsernameNotOccupiedError"

**Solution**: Channel name incorrect or channel doesn't exist.
- Verify channel name in `.env`
- Check channel exists on Telegram
- Use exact channel username (without @)

### Issue: Rate Limit Errors

**Solution**: Telegram API rate limiting. The scraper handles this automatically, but:
- Reduce `MAX_MESSAGES_PER_CHANNEL` if needed
- Add delays between channels (already implemented)
- Wait and retry later

### Issue: No Messages Scraped

**Possible Causes:**
1. Channel is private (requires invitation)
2. Channel has no messages
3. Authentication failed (check logs)

**Debug:**
```bash
# Check logs
tail -f logs/scraper_*.log

# Run with DEBUG level
export LOG_LEVEL=DEBUG
python -m src.scraper
```

---

## 📝 Next Steps (Future Tasks)

After Task-1 completion:

1. **Task-2**: Transform raw data using dbt
   - Create dimensional models
   - Build fact tables
   - Implement data quality checks

2. **Task-3**: Enrich with YOLO
   - Image analysis for medical products
   - Object detection and classification

3. **Task-4**: Expose via FastAPI
   - REST API for analytics
   - Real-time dashboards
   - Fraud detection endpoints

---

## 📚 Technical Stack

- **Python**: 3.11
- **Telethon**: Telegram MTProto API client
- **Docker**: Containerization for reproducibility
- **aiofiles**: Async file I/O
- **python-dotenv**: Environment variable management

---

## 📄 License & Credits

**Project**: Medical Telegram Warehouse  
**Organization**: Kara Solutions  
**Task**: Task-1 - Data Scraping & Collection  
**Architecture**: Modern ELT Pipeline  

---

## 🎓 Final Output Expectation

Upon completion, another senior engineer should be able to:

1. ✅ Clone the repository
2. ✅ Configure `.env` with credentials
3. ✅ Run `docker-compose up` and see data flow
4. ✅ Trust the data quality (valid JSON, proper structure)
5. ✅ Extend the pipeline (add channels, modify schema) without refactoring

**Data Trust Indicators:**
- Consistent JSON schema across all files
- Proper date partitioning
- Complete message metadata
- Image paths correctly referenced
- Comprehensive logs for auditability

---

**Status**: ✅ Task-1 Implementation Complete

**Branch**: `task-1-dev`  
**Ready for**: Testing, validation, and merge to `main`

