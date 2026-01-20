# Task-5: Pipeline Orchestration Documentation

**Status**: ✅ Complete
**Branch**: `task-5-dev`
**Orchestration Tool**: Dagster 1.7.0

---

## Overview

Task-5 transforms all prior tasks (1-4) into a **single automated production workflow** using Dagster, providing fintech-grade reliability, observability, and scheduling.

---

## Pipeline Design & DAG

### Execution Flow

```
┌─────────────────────────────┐
│  scrape_telegram_data       │  Task-1: Extract Telegram messages & images
│  (src/scraper.py)           │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  load_raw_to_postgres        │  Task-2: Load raw JSON → PostgreSQL
│  (scripts/load_raw_...)      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  run_dbt_transformations    │  Task-2: Create star schema (dbt)
│  (dbt run)                   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  run_yolo_enrichment         │  Task-3: YOLO object detection
│  (src/yolo_detect.py)        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  load_yolo_to_postgres      │  Task-3: Load YOLO CSV → PostgreSQL
│  (scripts/load_yolo_...)     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  run_dbt_yolo_model         │  Task-3: Create fct_image_detections
│  (dbt run --select ...)      │
└─────────────────────────────┘
```

### Dependency Chain

- **Sequential Execution**: Each op depends on the previous op's successful completion
- **Failure Handling**: Failures trigger retries (max 2 retries with 30-60s delay)
- **Loud Failures**: Pipeline stops on persistent failures with full error context

### Idempotency

All ops are designed to be idempotent (safe to re-run):

- **Telegram Scraper**: Checks existing files before scraping
- **PostgreSQL Loaders**: Use UPSERT logic to prevent duplicates
- **dbt Models**: Incremental/materialized tables handle re-runs gracefully
- **YOLO Detection**: Overwrites CSV output (idempotent by design)

---

## Execution Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `dagster==1.7.0`
- `dagster-webserver==1.7.0`
- All other project dependencies

### 2. Launch Dagster UI

```bash
dagster dev -f dagster_defs.py
```

**Output:**
```
Loading repository...
Serving on http://127.0.0.1:3000
```

### 3. Access Dagster UI

Open browser: [http://localhost:3000](http://localhost:3000)

**UI Features:**
- **Jobs**: View and execute pipeline jobs
- **Runs**: Monitor execution history
- **Schedules**: Configure and manage schedules
- **Assets**: View data assets (future enhancement)
- **Logs**: Inspect execution logs per op

### 4. Execute Pipeline

**Manual Execution:**
1. Navigate to "Jobs" → "medical_telegram_warehouse_pipeline"
2. Click "Launch Run"
3. Monitor execution in real-time

**Scheduled Execution:**
- Pipeline runs daily at 2:00 AM UTC
- Configure via "Schedules" tab in Dagster UI
- Enable/disable schedules as needed

**API Execution:**
```python
from dagster import DagsterInstance
from pipeline import medical_telegram_warehouse_pipeline

instance = DagsterInstance.ephemeral()
result = instance.create_run_for_job(
    job_def=medical_telegram_warehouse_pipeline,
    run_config={}
)
instance.submit_run(result)
```

### 5. Monitor Execution

**In Dagster UI:**
- View run status (queued → running → success/failure)
- Inspect logs per op
- Check execution metrics (duration, retries)
- Review failure alerts

**Log Output:**
Each op logs:
- Start/completion messages
- Subprocess stdout/stderr
- Error context on failures

**Example Log:**
```
2024-01-17 10:30:00 - INFO - ================================================================================
2024-01-17 10:30:00 - INFO - OP 1: Scraping Telegram Data (Task-1)
2024-01-17 10:30:00 - INFO - ================================================================================
2024-01-17 10:30:00 - INFO - Executing Python module: src.scraper
2024-01-17 10:35:00 - INFO - ✅ src.scraper completed successfully
2024-01-17 10:35:00 - INFO - ✅ Telegram scraping completed
```

### 6. Validate Results

After successful pipeline execution:

1. **Check PostgreSQL Tables:**
   ```sql
   SELECT COUNT(*) FROM raw.telegram_messages;
   SELECT COUNT(*) FROM marts.fct_messages;
   SELECT COUNT(*) FROM marts.fct_image_detections;
   ```

2. **Verify dbt Models:**
   ```bash
   dbt test
   ```

3. **Test FastAPI Endpoints:**
   ```bash
   curl http://localhost:8000/api/reports/top-products
   ```

---

## Monitoring Results & Insights

### Pipeline Metrics

**Typical Execution Times:**
- **scrape_telegram_data**: 2-5 minutes (depends on message volume)
- **load_raw_to_postgres**: 30-60 seconds
- **run_dbt_transformations**: 1-3 minutes
- **run_yolo_enrichment**: 3-10 minutes (depends on image count)
- **load_yolo_to_postgres**: 10-30 seconds
- **run_dbt_yolo_model**: 30-60 seconds

**Total Pipeline Duration**: ~5-15 minutes (varies with data volume)

### Observability Features

#### 1. Structured Logging

Each op logs:
- Start/completion timestamps
- Execution context
- Subprocess output
- Error messages with full stack traces

#### 2. Execution Tracking

- **Run Keys**: Unique identifiers for each run (idempotency)
- **Tags**: Metadata for filtering runs (scheduled, manual, etc.)
- **Timestamps**: Start/end times for all operations

#### 3. Failure Handling

**Retry Policies:**
- Max 2 retries per op
- Delay: 30-60 seconds between retries
- Transient errors (network, timeouts) are retried
- Persistent errors (syntax, config) fail loudly

**Error Context:**
- Full subprocess stdout/stderr
- Exception stack traces
- Environment variable validation
- File path verification

#### 4. Scheduling

**Daily Schedule:**
- **Cron**: `0 2 * * *` (2:00 AM UTC daily)
- **Status**: Enabled by default
- **Run Keys**: Include timestamp for idempotency

**Schedule Management:**
- Enable/disable via Dagster UI
- Modify cron expression as needed
- View schedule history

### Business Value

1. **Reliability**: Automated execution reduces manual errors
2. **Observability**: Full visibility into pipeline health
3. **Scalability**: Easy to add new ops or modify dependencies
4. **Maintainability**: Clear separation of concerns per op
5. **Production-Ready**: Fintech-grade orchestration standards

---

## Configuration

### Environment Variables

All ops use environment variables from `.env`:

```env
# Telegram (Task-1)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_CHANNELS=CheMed,Lobelia Cosmetics

# PostgreSQL (Task-2, Task-3)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=medical_warehouse
POSTGRES_USER=medical_user
POSTGRES_PASSWORD=medical_pass

# YOLO (Task-3)
YOLO_MODEL=yolov8n.pt
YOLO_CONFIDENCE_THRESHOLD=0.25
```

### Dagster Configuration

**Pipeline File**: `pipeline.py`
**Definitions File**: `dagster_defs.py`

**Modify Schedule:**
```python
@schedule(
    job=medical_telegram_warehouse_pipeline,
    cron_schedule="0 2 * * *",  # Change this
    ...
)
```

---

## Troubleshooting

### Common Issues

1. **Module Not Found Errors:**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`

2. **PostgreSQL Connection Errors:**
   - Verify PostgreSQL is running: `docker-compose up -d postgres`
   - Check environment variables in `.env`

3. **dbt Command Errors:**
   - Verify `profiles.yml` is configured
   - Check `dbt_project.yml` syntax

4. **YOLO Model Errors:**
   - Ensure `yolov8n.pt` exists in project root
   - Check image paths in `data/raw/images/`

### Debug Mode

Enable verbose logging:
```python
# In pipeline.py, modify logging level
logging.basicConfig(level=logging.DEBUG)
```

---

## Future Enhancements

1. **Asset Materialization**: Track data assets in Dagster
2. **Sensor-Based Triggers**: Trigger on file changes
3. **Parallel Execution**: Run independent ops in parallel
4. **External Monitoring**: Integrate with Datadog/Prometheus
5. **Alerting**: Email/Slack notifications on failures

---

## References

- **Dagster Documentation**: https://docs.dagster.io/
- **Pipeline Code**: [`pipeline.py`](../pipeline.py)
- **Definitions**: [`dagster_defs.py`](../dagster_defs.py)
- **Project README**: [`README.md`](../README.md)
