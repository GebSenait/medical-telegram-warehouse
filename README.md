# Medical Telegram Warehouse

**Enterprise-Grade ELT Pipeline for Ethiopian Medical/Pharmaceutical Telegram Channel Data**

**Organization**: Kara Solutions (Ethiopia)
**Project**: `medical-telegram-warehouse`

---

## 📑 Table of Contents

- [Business Understanding](#-business-understanding)
- [Architecture Overview](#-architecture-overview)
- [Task 1: Data Scraping & Collection](#-task-1-data-scraping--collection)
  - [Implementation Details](#task-1-implementation-details)
  - [Results & Insights](#task-1-results--insights)
- [Task 2: Data Modeling & Transformation](#-task-2-data-modeling--transformation)
  - [Implementation Details](#task-2-implementation-details)
  - [Star Schema Design Decisions](#star-schema-design-decisions)
  - [Results & Insights](#task-2-results--insights)
- [Next Steps](#-next-steps)

---

## 🎯 Business Understanding

This project extracts insights from public Ethiopian medical and pharmaceutical Telegram channels, applying fintech fraud detection principles (anomaly detection, volume spikes, behavior patterns) to the medical/pharmaceutical domain.

The pipeline transforms raw Telegram data into a trusted analytical warehouse, enabling insights similar to fintech fraud detection:
- **Volume anomalies**: Detect unusual posting patterns
- **Behavior patterns**: Identify channel-specific characteristics
- **Content richness**: Analyze message quality and media presence
- **Temporal trends**: Track engagement over time

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│  Telegram API   │
└────────┬────────┘
         │
         │ Extract
         ▼
┌─────────────────┐
│  Raw Data Lake  │ ◄── Task-1 ✅
│  (JSON Files)   │
└────────┬────────┘
         │
         │ Load
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   (raw schema)  │
└────────┬────────┘
         │
         │ Transform
         ▼
┌─────────────────┐
│   dbt Layer     │ ◄── Task-2 ✅
│ (Star Schema)   │
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

---

## 📊 Task 1: Data Scraping & Collection

**Status**: ✅ Complete
**Branch**: `task-1-dev`
**Implementation**: [See below](#task-1-implementation-details)

### Task-1 Implementation Details

Task-1 extracts raw Telegram data and loads it into the raw data lake (JSON files). This is the foundation that all downstream analytics depend on.

**Key Features:**
- ✅ Idempotent operations: Safe to re-run without duplicating data
- ✅ Date partitioning: Messages stored by date for efficient querying
- ✅ Image download: Automatic image extraction and storage
- ✅ Error handling: Graceful handling of rate limits, network errors
- ✅ Logging: Comprehensive logging for debugging and monitoring
- ✅ Non-blocking I/O: Async operations for performance

**Data Storage:**
- **Messages**: `data/raw/telegram_messages/YYYY-MM-DD/channel_name.json`
- **Images**: `data/raw/images/channel_name/message_id.jpg`

**Message Schema (JSON):**
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

### Task-1 Results & Insights

- **Implementation Location**: [`src/scraper.py`](src/scraper.py)
- **Execution Script**: `python -m src.scraper`
- **Docker Support**: Included in `docker-compose.yml`
- **Configuration**: Environment variables in `.env`

[Full Task-1 Documentation](#-task-1-full-documentation)

---

## 🔄 Task 2: Data Modeling & Transformation

**Status**: ✅ Complete
**Branch**: `task-2-dev`
**Implementation**: [See below](#task-2-implementation-details)

### Task-2 Implementation Details

Task-2 transforms raw Telegram JSON data into a trusted analytical warehouse using **PostgreSQL + dbt** with a **dimensional star schema**.

**Components:**

1. **Raw Data Loading** (`scripts/load_raw_to_postgres.py`)
   - Loads JSON files from `data/raw/telegram_messages/` into PostgreSQL
   - Creates `raw.telegram_messages` table with indexes
   - Supports upsert (idempotent loading)

2. **Staging Models** (`models/staging/`)
   - `stg_telegram_messages`: Data cleaning, type casting, derived fields
   - Casts all data types correctly
   - Adds `message_length` and `has_image` derived fields
   - Filters invalid records (null message_id, channel_name, message_date)

3. **Star Schema Marts** (`models/marts/`)
   - **`dim_channels`**: Channel dimension with surrogate keys
   - **`dim_dates`**: Date dimension (2020-2030) with calendar attributes
   - **`fct_messages`**: Message fact table with foreign keys

4. **Data Quality Tests**
   - Schema tests: `unique`, `not_null`, `relationships`
   - Custom business tests:
     - `test_no_future_dated_messages.sql`: No future-dated messages
     - `test_no_negative_views.sql`: No negative view counts

5. **Documentation**
   - dbt docs generated with model and column descriptions
   - README updated with Task-1 and Task-2 sections

### Star Schema Design Decisions

**Why Star Schema?**

1. **Analytical Performance**: Star schema is optimized for analytical queries (COUNT, SUM, GROUP BY). Fact table stores measures, dimensions provide context.
2. **Business User Friendly**: Simple to understand—fact table = events, dimensions = context.
3. **Query Simplicity**: Joins are straightforward (fact → dimensions via foreign keys).
4. **Scalability**: Dimensions can be enriched independently without touching fact table.

**Dimension Design:**

- **`dim_channels`**:
  - **Grain**: One row per unique channel
  - **Surrogate Key**: `channel_key` (MD5 hash of `channel_name`)
  - **Business Key**: `channel_name`
  - **Attributes**: `first_message_date`, `last_message_date`, `total_messages`
  - **Use Case**: Channel-level analytics, comparisons

- **`dim_dates`**:
  - **Grain**: One row per calendar day (2020-2030)
  - **Surrogate Key**: `date_key` (YYYYMMDD integer)
  - **Attributes**: Year, quarter, month, week, day_of_month, day_of_week, day_name, is_weekend
  - **Use Case**: Time-based analysis, trending, seasonality

**Fact Table Design:**

- **`fct_messages`**:
  - **Grain**: One row per message
  - **Primary Key**: `message_id` (business key)
  - **Foreign Keys**: `channel_key`, `date_key`
  - **Measures**: `views`, `forwards`, `message_length`
  - **Flags**: `has_media`, `has_image`
  - **Use Case**: Message-level analytics, volume analysis, engagement metrics

**Why These Dimensions?**

- **Channels**: Core business entity—analytics often group by channel
- **Dates**: Essential for time-series analysis, trending, anomaly detection
- **No Message Dimension**: Message attributes (text, length, media) are stored in fact for simplicity (not normalized separately)

**Surrogate Keys Rationale:**

- **`channel_key`**: MD5 hash of `channel_name`—consistent, immutable
- **`date_key`**: YYYYMMDD integer—efficient joins, human-readable
- **Benefits**: Independent of business keys, enables SCD Type 2 if needed later

### Task-2 Results & Insights

- **dbt Project**: [`dbt_project.yml`](dbt_project.yml)
- **Raw Loader**: [`scripts/load_raw_to_postgres.py`](scripts/load_raw_to_postgres.py)
- **Staging Models**: [`models/staging/`](models/staging/)
- **Mart Models**: [`models/marts/`](models/marts/)
- **Tests**: [`tests/`](tests/)
- **Documentation**: Run `dbt docs generate` and `dbt docs serve`

**Execution Steps:**

```bash
# 1. Load raw data into PostgreSQL
python scripts/load_raw_to_postgres.py

# 2. Run dbt models
dbt run

# 3. Run tests
dbt test

# 4. Generate docs
dbt docs generate
dbt docs serve
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+ (or Docker)
- dbt-postgres 1.7+

### Setup

1. **Clone repository**
   ```bash
   git clone <repo-url>
   cd medical-telegram-warehouse
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Copy .env.example to .env and fill in values
   cp .env.example .env
   ```

4. **Start PostgreSQL** (via Docker)
   ```bash
   docker-compose up -d postgres
   ```

5. **Load raw data** (Task-1)
   ```bash
   python -m src.scraper
   ```

6. **Load into PostgreSQL** (Task-2)
   ```bash
   python scripts/load_raw_to_postgres.py
   ```

7. **Transform with dbt** (Task-2)
   ```bash
   dbt run
   dbt test
   dbt docs generate
   ```

---

## 📋 Git Workflow

**Current Branch**: `task-2-dev`

```bash
# Switch branches
git checkout main          # Switch to main
git checkout task-2-dev    # Switch to task-2-dev

# Create new task branch
git checkout main
git checkout -b task-3-dev
```

---

## 🏗️ Project Structure

```
medical-telegram-warehouse/
├── .gitignore
├── .env                      # Environment variables (not committed)
├── docker-compose.yml        # PostgreSQL + Telegram scraper services
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── src/                      # Task-1: Data Scraping
│   ├── scraper.py
│   └── __init__.py
│
├── scripts/                  # Task-2: Data Loading
│   └── load_raw_to_postgres.py
│
├── models/                   # Task-2: dbt Models
│   ├── staging/
│   │   ├── stg_telegram_messages.sql
│   │   ├── schema.yml
│   │   └── _sources.yml
│   └── marts/
│       ├── dim_channels.sql
│       ├── dim_dates.sql
│       ├── fct_messages.sql
│       ├── schema.yml
│       └── _models.yml
│
├── tests/                    # Task-2: Custom Tests
│   ├── test_no_future_dated_messages.sql
│   └── test_no_negative_views.sql
│
├── macros/                   # Task-2: dbt Macros
│   └── surrogate_key.sql
│
├── dbt_project.yml           # Task-2: dbt Configuration
├── profiles.yml              # Task-2: dbt Profiles (not committed)
│
├── data/                     # Task-1: Raw Data Lake
│   └── raw/
│       ├── telegram_messages/
│       └── images/
│
└── logs/                     # Task-1: Execution Logs
```

---

## 🔍 Task 1: Full Documentation

### Environment Variables

```env
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION_NAME=telegram_scraper
TELEGRAM_CHANNELS=CheMed,Lobelia Cosmetics,Tikvah Pharma
MAX_MESSAGES_PER_CHANNEL=1000
SCRAPER_BATCH_SIZE=100
LOG_LEVEL=INFO
```

### Execution

**Docker:**
```bash
docker-compose up telegram-scraper
```

**Local Python:**
```bash
python -m src.scraper
```

### Validation Checklist

- [x] Repository initialized
- [x] `main` branch exists
- [x] `task-1-dev` branch exists
- [x] Scraper runs without errors
- [x] JSON files created in `data/raw/telegram_messages/YYYY-MM-DD/`
- [x] Images downloaded to `data/raw/images/channel_name/`

---

## 🔄 Task 2: Full Documentation

### PostgreSQL Configuration

**Environment Variables:**
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=medical_warehouse
POSTGRES_USER=medical_user
POSTGRES_PASSWORD=medical_pass
```

**Docker:**
```bash
docker-compose up -d postgres
```

### dbt Configuration

**Profiles Location**: `~/.dbt/profiles.yml` or set `DBT_PROFILES_DIR`

**Profile Name**: `medical_warehouse`

### Execution Steps

1. **Load Raw Data:**
   ```bash
   python scripts/load_raw_to_postgres.py
   ```

2. **Run dbt Models:**
   ```bash
   dbt run
   ```

3. **Run Tests:**
   ```bash
   dbt test
   ```

4. **Generate Documentation:**
   ```bash
   dbt docs generate
   dbt docs serve
   ```

### Validation Checklist

- [x] PostgreSQL accessible and schema created
- [x] Raw data loaded into `raw.telegram_messages`
- [x] Staging models created (`staging.stg_telegram_messages`)
- [x] Mart models created (`marts.dim_channels`, `marts.dim_dates`, `marts.fct_messages`)
- [x] All dbt tests passing
- [x] dbt documentation generated
- [x] README updated with Task-1 and Task-2 sections

---

## 📝 Next Steps

1. **Task-3**: Enrich with YOLO
   - Image analysis for medical products
   - Object detection and classification

2. **Task-4**: Expose via FastAPI
   - REST API for analytics
   - Real-time dashboards
   - Fraud detection endpoints

---

## 📚 Technical Stack

### Task-1 (Extract & Load)
- **Python**: 3.11
- **Telethon**: Telegram MTProto API client
- **Docker**: Containerization
- **aiofiles**: Async file I/O
- **python-dotenv**: Environment variable management

### Task-2 (Transform)
- **PostgreSQL**: 16+
- **dbt**: 1.7+ (dbt-postgres)
- **psycopg2**: PostgreSQL adapter
- **Docker Compose**: PostgreSQL service

---

## 📄 License & Credits

**Project**: Medical Telegram Warehouse
**Organization**: Kara Solutions (Ethiopia)
**Architecture**: Modern ELT Pipeline
**Status**: Task-1 ✅ | Task-2 ✅ | Task-3 ⏳ | Task-4 ⏳

---

## 🎓 Final Output Expectation

Upon completion, another senior engineer should be able to:

1. ✅ Clone the repository
2. ✅ Configure `.env` with credentials
3. ✅ Run `docker-compose up` and see data flow from Telegram → JSON → PostgreSQL → dbt
4. ✅ Trust the data quality (valid JSON, proper schema, passing tests)
5. ✅ Extend the pipeline (add channels, modify models) without refactoring

**Data Trust Indicators:**
- Consistent JSON schema across all files
- Proper date partitioning
- Complete message metadata
- Star schema with enforced referential integrity
- Comprehensive data quality tests
- Generated dbt documentation

---
