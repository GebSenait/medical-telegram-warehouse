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
- [Task 3: Data Enrichment with Object Detection (YOLO)](#-task-3-data-enrichment-with-object-detection-yolo)
  - [Implementation Details](#task-3-implementation-details)
  - [Analysis & Insights](#task-3-analysis--insights)
  - [Results & Limitations](#task-3-results--limitations)
- [Task 4: Analytical API (FastAPI)](#-task-4-analytical-api-fastapi)
  - [Implementation Details](#task-4-implementation-details)
  - [API Endpoints](#api-endpoints)
  - [Query Logic & Analysis](#query-logic--analysis)
  - [Results & Insights](#task-4-results--insights)
- [Task 5: Pipeline Orchestration (Dagster)](#-task-5-pipeline-orchestration-dagster)
  - [Implementation Details](#task-5-implementation-details)
  - [Pipeline Design & DAG](#pipeline-design--dag)
  - [Execution Steps](#task-5-execution-steps)
  - [Monitoring Results & Insights](#task-5-monitoring-results--insights)
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
│   YOLO Layer    │ ◄── Task-3 ✅
└────────┬────────┘
         │
         │ Expose
         ▼
┌─────────────────┐
│   FastAPI       │ ◄── Task-4 ✅
└─────────────────┘
         │
         │ Orchestrate
         ▼
┌─────────────────┐
│   Dagster       │ ◄── Task-5 ✅
│  (Orchestration)│
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
├── api/                      # Task-4: FastAPI Analytical API
│   ├── main.py              # FastAPI app & routes
│   ├── database.py          # DB engine/session
│   ├── schemas.py           # Pydantic models
│   └── __init__.py
│
├── src/                      # Task-1 & Task-3: Data Processing
│   ├── scraper.py
│   ├── yolo_detect.py
│   └── __init__.py
│
├── scripts/                  # Task-2 & Task-3: Data Loading
│   ├── load_raw_to_postgres.py
│   └── load_yolo_to_postgres.py
│
├── models/                   # Task-2 & Task-3: dbt Models
│   ├── staging/
│   │   ├── stg_telegram_messages.sql
│   │   ├── schema.yml
│   │   └── _sources.yml
│   └── marts/
│       ├── dim_channels.sql
│       ├── dim_dates.sql
│       ├── fct_messages.sql
│       ├── fct_image_detections.sql
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
├── data/                     # Task-1 & Task-3: Raw Data Lake
│   └── raw/
│       ├── telegram_messages/
│       ├── images/
│       └── processed/
│           └── yolo_detections.csv
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

## 🖼️ Task 3: Full Documentation

### Environment Variables

```env
# YOLO Configuration
YOLO_MODEL=yolov8n.pt
YOLO_CONFIDENCE_THRESHOLD=0.25
YOLO_OUTPUT_CSV=data/processed/yolo_detections.csv
DATA_RAW_IMAGES=data/raw/images
```

### Execution Steps

1. **Run YOLO Detection:**
   ```bash
   python -m src.yolo_detect
   ```

2. **Load Detection Results:**
   ```bash
   python scripts/load_yolo_to_postgres.py
   ```

3. **Run dbt Models:**
   ```bash
   dbt run --select fct_image_detections
   ```

4. **Run Tests:**
   ```bash
   dbt test --select fct_image_detections
   ```

### Validation Checklist

- [x] YOLO model loads successfully
- [x] Detection script processes images
- [x] CSV output created with detection results
- [x] Data loaded into `raw.yolo_detections`
- [x] dbt model `fct_image_detections` created
- [x] Foreign key relationships validated
- [x] Schema tests passing
- [x] Analysis documentation complete
- [x] README updated with Task-3 section

---

## 🖼️ Task 3: Data Enrichment with Object Detection (YOLO)

**Status**: ✅ Complete
**Branch**: `task-3-dev`
**Implementation**: [See below](#task-3-implementation-details)

### Task-3 Implementation Details

Task-3 enriches the analytical warehouse with **visual intelligence** using YOLOv8 object detection. This adds image-derived features that help answer critical business questions about visual content strategy and engagement patterns.

**Components:**

1. **YOLO Detection Script** (`src/yolo_detect.py`)
   - Uses YOLOv8 nano model (`yolov8n.pt`) for performance on laptops
   - Scans `data/raw/images/` directory recursively
   - Runs object detection on each image
   - Classifies images into categories:
     - **promotional**: person + product detected
     - **product_display**: product only
     - **lifestyle**: person only
     - **other**: no relevant objects detected
   - Outputs CSV with detection results

2. **Data Loading** (`scripts/load_yolo_to_postgres.py`)
   - Loads YOLO detection CSV into PostgreSQL `raw.yolo_detections` table
   - Supports upsert (idempotent loading)
   - Creates indexes for performance

3. **dbt Integration** (`models/marts/fct_image_detections.sql`)
   - Joins YOLO detections with `fct_messages`
   - Enriches with engagement metrics (views, forwards)
   - Links to dimensions (channel_key, date_key)
   - Provides unified view for image content analysis

**Image Classification Logic:**

The classification uses detected object classes from YOLO's COCO dataset:
- **Person detection** (class 0): Indicates human presence
- **Product detection** (classes 39-79): Common product-related objects (bottles, cups, etc.)
- **Combination logic**: Determines image category based on presence of person and/or product

**Model Choice: YOLOv8 Nano**

- **Performance**: Fast inference on CPU/laptop hardware
- **Accuracy**: Reasonable for common object detection tasks
- **Trade-off**: Optimized for speed over maximum accuracy
- **Use Case**: Production-grade enrichment layer for analytics

### Task-3 Analysis & Insights

**Business Questions Answered:**

1. **Which channels rely more on visuals?**
   - Analysis available in `fct_image_detections` grouped by `channel_key`
   - Compare `num_detections` and `image_category` distribution across channels

2. **Do images with people drive more engagement?**
   - Compare `views` and `forwards` by `image_category`
   - Promotional images (person + product) vs. product-only images

3. **What are the limitations of generic CV models?**
   - YOLOv8 is trained on COCO dataset (general objects)
   - Medical/pharmaceutical products may not be in COCO classes
   - Domain-specific fine-tuning would improve accuracy

**Full Analysis**: See [Task-3 Analysis Document](docs/task-3-analysis.md)

### Task-3 Results & Limitations

**Deliverables:**
- ✅ `src/yolo_detect.py` - YOLO detection script
- ✅ `scripts/load_yolo_to_postgres.py` - Data loader
- ✅ `models/marts/fct_image_detections.sql` - dbt enrichment model
- ✅ YOLO detection results CSV
- ✅ Analysis documentation

**Execution Steps:**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run YOLO detection on images
python -m src.yolo_detect

# 3. Load detection results into PostgreSQL
python scripts/load_yolo_to_postgres.py

# 4. Run dbt models
dbt run --select fct_image_detections

# 5. Run tests
dbt test --select fct_image_detections
```

**Limitations & Future Improvements:**

1. **Generic Model Limitations**:
   - YOLOv8 trained on COCO (80 classes) - may miss medical-specific products
   - Confidence scores may be lower for domain-specific objects
   - Solution: Fine-tune on medical product dataset

2. **Classification Logic**:
   - Current logic uses simple heuristics (person + product)
   - Could be enhanced with ML-based image classification
   - Solution: Train custom classifier on labeled medical commerce images

3. **Performance**:
   - Processing time scales with number of images
   - Consider batch processing or GPU acceleration for large datasets
   - Solution: Implement parallel processing or GPU inference

**Full Documentation**: [Task-3 Analysis](docs/task-3-analysis.md)

---

## 🚀 Task 4: Analytical API (FastAPI)

**Status**: ✅ Complete
**Branch**: `task-4-dev`
**Implementation**: [See below](#task-4-implementation-details)

### Task-4 Implementation Details

Task-4 exposes the **dbt data marts** through a **FastAPI REST API** that answers key business questions clearly, safely, and efficiently. This API layer enables decision-makers to access trusted analytical insights from Telegram data.

**Components:**

1. **FastAPI Application** (`api/main.py`)
   - Production-ready REST API with auto-generated OpenAPI documentation
   - 4 analytical endpoints querying dbt marts
   - Comprehensive error handling and validation
   - Health check and database connectivity verification

2. **Database Connection Layer** (`api/database.py`)
   - SQLAlchemy engine and session management
   - Connection pooling for performance
   - Environment-based configuration via `.env`

3. **Pydantic Schemas** (`api/schemas.py`)
   - Type-safe request/response models
   - Clear API contracts with examples
   - Validation and serialization

**API Architecture:**

```
┌─────────────────┐
│   FastAPI App   │
│  (api/main.py)  │
└────────┬────────┘
         │
         │ SQLAlchemy
         ▼
┌─────────────────┐
│   PostgreSQL    │
│  (dbt marts)    │
│  - dim_channels │
│  - dim_dates    │
│  - fct_messages │
│  - fct_image_   │
│    detections   │
└─────────────────┘
```

### API Endpoints

#### 1. **Top Products** - `GET /api/reports/top-products`

**Business Question**: What are the most frequently mentioned products/terms across all channels?

**Query Logic**:
- Extracts terms from `message_text` using PostgreSQL text functions
- Aggregates by term (case-insensitive)
- Ranks by mention count
- Includes engagement metrics (views, forwards) per term
- Filters out very short words and pure numbers

**Parameters**:
- `limit` (default: 10, max: 100): Number of top products to return
- `min_mentions` (default: 1): Minimum mention count threshold

**Response**: List of top products with mention counts, engagement metrics, and channels

**Example**:
```bash
GET /api/reports/top-products?limit=10&min_mentions=5
```

#### 2. **Channel Activity** - `GET /api/channels/{channel_name}/activity`

**Business Question**: What are the posting volume and engagement trends for a specific channel?

**Query Logic**:
- Joins `fct_messages` with `dim_dates` and `dim_channels`
- Groups messages by day or week
- Calculates message counts, total views/forwards
- Computes average engagement per message
- Supports configurable date range

**Parameters**:
- `channel_name` (path): Name of the Telegram channel
- `period` (query, default: "daily"): Aggregation period - "daily" or "weekly"
- `days_back` (query, default: 30): Number of days to look back (1-365)

**Response**: Activity trends by period with engagement metrics

**Example**:
```bash
GET /api/channels/CheMed/activity?period=daily&days_back=30
```

#### 3. **Message Search** - `GET /api/search/messages`

**Business Question**: Find specific products, medications, or topics mentioned across channels.

**Query Logic**:
- Full-text search in `message_text` (case-insensitive LIKE)
- Joins with `dim_channels` for channel names
- Supports optional channel filtering
- Returns matching messages with engagement metrics
- Orders by timestamp (most recent first)

**Parameters**:
- `query` (required): Search keyword
- `limit` (default: 20, max: 100): Maximum number of results
- `channel_name` (optional): Filter by channel name

**Response**: Matching messages with metadata

**Example**:
```bash
GET /api/search/messages?query=paracetamol&limit=20&channel_name=CheMed
```

#### 4. **Visual Content Stats** - `GET /api/reports/visual-content`

**Business Question**: What are the image usage patterns and YOLO object detection insights?

**Query Logic**:
- Aggregates data from `fct_image_detections`
- Groups by image category and detected class
- Calculates total images, detections, averages
- Computes engagement metrics by category
- Identifies top detected object classes

**Response**: Comprehensive visual content statistics

**Example**:
```bash
GET /api/reports/visual-content
```

### Query Logic & Analysis

**Design Principles**:

1. **Query dbt Marts Only**: All endpoints query the `marts` schema (star schema), not raw data
2. **Efficient Joins**: Leverages foreign keys (channel_key, date_key) for fast joins
3. **Aggregation at Database**: Heavy lifting done in PostgreSQL, not Python
4. **Type Safety**: Pydantic schemas ensure type-safe request/response handling
5. **Error Handling**: Graceful handling of missing data, invalid inputs, database errors

**Performance Considerations**:

- Connection pooling via SQLAlchemy (pool_size=5, max_overflow=10)
- Indexed foreign keys in fact tables for fast joins
- Text search uses PostgreSQL native functions (no external search engine needed)
- Pagination via LIMIT to prevent large result sets

**Security**:

- No SQL injection risk (parameterized queries via SQLAlchemy)
- Input validation via Pydantic and FastAPI Query parameters
- Environment-based credentials (never hardcoded)

### Task-4 Results & Insights

**Deliverables:**
- ✅ `api/main.py` - FastAPI application with 4 endpoints
- ✅ `api/database.py` - Database connection layer
- ✅ `api/schemas.py` - Pydantic request/response models
- ✅ `requirements.txt` - Updated with FastAPI dependencies
- ✅ Auto-generated OpenAPI documentation at `/docs`
- ✅ Health check endpoint at `/health`
- ✅ Comprehensive error handling

**Execution Steps:**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Ensure PostgreSQL is running and dbt marts exist
docker-compose up -d postgres
dbt run

# 3. Start FastAPI server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Access API documentation
# Open browser: http://localhost:8000/docs
```

**API Documentation:**

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

**Validation Checklist:**

- [x] FastAPI application starts without errors
- [x] Database connection verified on startup
- [x] All 4 endpoints implemented and functional
- [x] Pydantic schemas validate requests/responses
- [x] Error handling for missing data and invalid inputs
- [x] OpenAPI documentation auto-generated
- [x] Health check endpoint working
- [x] README updated with Task-4 documentation

**Business Value:**

1. **Decision-Making**: Executives can query top products, channel activity, and trends via REST API
2. **Integration Ready**: API can be consumed by dashboards, BI tools, or other applications
3. **Real-Time Insights**: Fast queries on pre-aggregated dbt marts (no raw data scanning)
4. **Scalable**: Connection pooling and efficient queries support concurrent users
5. **Trusted Data**: Only queries validated dbt marts (star schema), ensuring data quality

**Full Documentation**: See API documentation at `/docs` endpoint

---

## 🔄 Task 5: Pipeline Orchestration (Dagster)

**Status**: ✅ Complete
**Branch**: `task-5-dev`
**Implementation**: [See below](#task-5-implementation-details)

### Task-5 Implementation Details

Task-5 transforms all prior tasks into a **single automated production workflow** using **Dagster**, providing fintech-grade reliability, observability, and scheduling.

**Components:**

1. **Dagster Pipeline** (`pipeline.py`)
   - 6 orchestrated ops with explicit dependencies
   - Retry policies for resilience
   - Comprehensive logging at each step
   - Idempotent operations

2. **Pipeline Ops:**
   - `scrape_telegram_data`: Runs Task-1 scraper
   - `load_raw_to_postgres`: Loads raw JSON into PostgreSQL
   - `run_dbt_transformations`: Executes dbt star schema models
   - `run_yolo_enrichment`: Runs YOLO object detection
   - `load_yolo_to_postgres`: Loads YOLO results into PostgreSQL
   - `run_dbt_yolo_model`: Creates enriched fact table

3. **Scheduling** (`daily_pipeline_schedule`)
   - Daily execution at 2:00 AM UTC
   - Configurable via Dagster UI
   - Run keys for idempotency

4. **Observability:**
   - Structured logging at each op
   - Execution context tracking
   - Failure alerts via Dagster UI
   - Run history and metrics

### Pipeline Design & DAG

**Execution Flow:**

```
┌─────────────────────────┐
│ scrape_telegram_data    │ ◄── Task-1: Extract
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ load_raw_to_postgres    │ ◄── Task-2: Load Raw
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ run_dbt_transformations  │ ◄── Task-2: Transform
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ run_yolo_enrichment     │ ◄── Task-3: YOLO Detection
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ load_yolo_to_postgres   │ ◄── Task-3: Load YOLO
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ run_dbt_yolo_model      │ ◄── Task-3: Enrich Fact
└─────────────────────────┘
```

**Dependency Chain:**
- Each op depends on the previous op's successful completion
- Failures trigger retries (max 2 retries with 30-60s delay)
- Pipeline stops on persistent failures (loud failure)

**Idempotency:**
- All ops are idempotent (safe to re-run)
- Telegram scraper: Checks existing files before scraping
- PostgreSQL loaders: Use UPSERT logic
- dbt models: Incremental/materialized tables

### Task-5 Execution Steps

**1. Install Dagster:**

```bash
pip install -r requirements.txt
```

**2. Launch Dagster UI:**

```bash
dagster dev -f dagster_defs.py
```

**3. Access Dagster UI:**

Open browser: [http://localhost:3000](http://localhost:3000)

**4. Execute Pipeline:**

- **Manual Execution**: Click "Launch Run" in Dagster UI
- **Scheduled Execution**: Pipeline runs daily at 2:00 AM UTC
- **API Execution**: Use Dagster GraphQL API

**5. Monitor Execution:**

- View run status in Dagster UI
- Inspect logs per op
- Check execution metrics
- Review failure alerts

**6. Validate Results:**

- Check PostgreSQL tables are updated
- Verify dbt models are refreshed
- Confirm YOLO detections are loaded
- Test FastAPI endpoints return latest data

### Task-5 Monitoring Results & Insights

**Pipeline Metrics:**

- **Execution Time**: ~5-15 minutes (depends on data volume)
- **Success Rate**: Monitored via Dagster UI
- **Failure Points**: Logged with full context
- **Retry Behavior**: Automatic retries on transient failures

**Observability Features:**

1. **Structured Logging:**
   - Each op logs start/completion
   - Error messages with full context
   - Subprocess stdout/stderr captured

2. **Execution Tracking:**
   - Run keys for idempotency
   - Tags for filtering runs
   - Timestamps for all operations

3. **Failure Handling:**
   - Retry policies on transient errors
   - Loud failures on persistent errors
   - Full error context in logs

4. **Scheduling:**
   - Daily schedule at 2:00 AM UTC
   - Configurable via Dagster UI
   - Run history tracking

**Business Value:**

1. **Reliability**: Automated execution reduces manual errors
2. **Observability**: Full visibility into pipeline health
3. **Scalability**: Easy to add new ops or modify dependencies
4. **Maintainability**: Clear separation of concerns per op
5. **Production-Ready**: Fintech-grade orchestration standards

**Full Documentation**: See [Pipeline Documentation](docs/task-5-pipeline-documentation.md)

---

## 📝 Next Steps

1. **Enhanced Monitoring**:
   - Integrate with monitoring tools (Datadog, Prometheus)
   - Set up alerting for pipeline failures
   - Create dashboards for pipeline metrics

2. **Real-time Dashboards**:
   - Connect BI tools to FastAPI endpoints
   - Build interactive dashboards
   - Set up data freshness monitoring

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

### Task-3 (Enrich)
- **YOLOv8**: 8.1.0 (ultralytics)
- **Pillow**: 10.2.0 (image processing)
- **Pandas**: 2.2.0 (data processing)

### Task-4 (Expose)
- **FastAPI**: 0.109.0 (REST API framework)
- **Uvicorn**: 0.27.0 (ASGI server)
- **SQLAlchemy**: 2.0.25 (ORM and database toolkit)
- **Pydantic**: 2.5.3 (data validation)

---

## 📄 License & Credits

**Project**: Medical Telegram Warehouse
**Organization**: Kara Solutions (Ethiopia)
**Architecture**: Modern ELT Pipeline
**Status**: Task-1 ✅ | Task-2 ✅ | Task-3 ✅ | Task-4 ✅ | Task-5 ✅

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
