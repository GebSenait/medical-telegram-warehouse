"""
Dagster Pipeline Orchestration for Medical Telegram Warehouse
Task-5: Production-Grade Pipeline Orchestration

This pipeline orchestrates the entire data product:
Telegram → Data Lake → PostgreSQL → dbt Star Schema → YOLO Enrichment → FastAPI API

Pipeline DAG:
scrape_telegram_data → load_raw_to_postgres → run_dbt_transformations → run_yolo_enrichment → load_yolo_to_postgres → run_dbt_yolo_model
"""

import os
import subprocess
import sys
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from dagster import (
    op,
    job,
    schedule,
    DefaultSensorStatus,
    RunRequest,
    SkipReason,
    ScheduleEvaluationContext,
    RetryPolicy,
    OpExecutionContext,
)

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Paths
PROJECT_ROOT = Path(__file__).parent
SCRAPER_MODULE = "src.scraper"
YOLO_MODULE = "src.yolo_detect"
LOAD_RAW_SCRIPT = PROJECT_ROOT / "scripts" / "load_raw_to_postgres.py"
LOAD_YOLO_SCRIPT = PROJECT_ROOT / "scripts" / "load_yolo_to_postgres.py"

# Environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "medical_warehouse")
POSTGRES_USER = os.getenv("POSTGRES_USER", "medical_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "medical_pass")


# ============================================================================
# Helper Functions
# ============================================================================


def run_python_module(module_name: str, context: OpExecutionContext) -> Dict[str, Any]:
    """
    Execute a Python module as a subprocess with proper error handling.

    Args:
        module_name: Python module to run (e.g., "src.scraper")
        context: Dagster execution context for logging

    Returns:
        Dictionary with execution results

    Raises:
        Exception: If subprocess fails
    """
    context.log.info(f"Executing Python module: {module_name}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", module_name],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )

        context.log.info(f"✅ {module_name} completed successfully")
        context.log.debug(f"stdout: {result.stdout}")

        if result.stderr:
            context.log.warning(f"stderr: {result.stderr}")

        return {
            "status": "success",
            "module": module_name,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.CalledProcessError as e:
        context.log.error(f"❌ {module_name} failed with exit code {e.returncode}")
        context.log.error(f"stdout: {e.stdout}")
        context.log.error(f"stderr: {e.stderr}")
        raise Exception(f"Module {module_name} failed: {e.stderr}") from e


def run_python_script(script_path: Path, context: OpExecutionContext) -> Dict[str, Any]:
    """
    Execute a Python script with proper error handling.

    Args:
        script_path: Path to Python script
        context: Dagster execution context for logging

    Returns:
        Dictionary with execution results

    Raises:
        Exception: If subprocess fails
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    context.log.info(f"Executing Python script: {script_path}")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )

        context.log.info(f"✅ {script_path.name} completed successfully")
        context.log.debug(f"stdout: {result.stdout}")

        if result.stderr:
            context.log.warning(f"stderr: {result.stderr}")

        return {
            "status": "success",
            "script": str(script_path),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.CalledProcessError as e:
        context.log.error(f"❌ {script_path.name} failed with exit code {e.returncode}")
        context.log.error(f"stdout: {e.stdout}")
        context.log.error(f"stderr: {e.stderr}")
        raise Exception(f"Script {script_path.name} failed: {e.stderr}") from e


def run_dbt_command(
    command: str, context: OpExecutionContext, select: str = None
) -> Dict[str, Any]:
    """
    Execute a dbt command with proper error handling.

    Args:
        command: dbt command (e.g., "run", "test")
        context: Dagster execution context for logging
        select: Optional model selection (e.g., "fct_image_detections")

    Returns:
        Dictionary with execution results

    Raises:
        Exception: If dbt command fails
    """
    dbt_cmd = ["dbt", command]

    if select:
        dbt_cmd.extend(["--select", select])

    context.log.info(f"Executing dbt command: {' '.join(dbt_cmd)}")

    try:
        result = subprocess.run(
            dbt_cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            env=os.environ.copy(),
        )

        context.log.info(f"✅ dbt {command} completed successfully")
        context.log.debug(f"stdout: {result.stdout}")

        if result.stderr:
            context.log.warning(f"stderr: {result.stderr}")

        return {
            "status": "success",
            "command": command,
            "select": select,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.CalledProcessError as e:
        context.log.error(f"❌ dbt {command} failed with exit code {e.returncode}")
        context.log.error(f"stdout: {e.stdout}")
        context.log.error(f"stderr: {e.stderr}")
        raise Exception(f"dbt {command} failed: {e.stderr}") from e


# ============================================================================
# Dagster Ops
# ============================================================================


@op(
    description="Scrape Telegram channels and save raw data to data lake (Task-1)",
    retry_policy=RetryPolicy(max_retries=2, delay=60),
    tags={"task": "task-1", "layer": "extract"},
)
def scrape_telegram_data(context: OpExecutionContext) -> Dict[str, Any]:
    """
    Op 1: Scrape Telegram channels using Task-1 scraper.

    This op runs the Telegram scraper to extract messages and images
    from configured channels and saves them to the raw data lake.

    Returns:
        Dictionary with scraping statistics
    """
    context.log.info("=" * 80)
    context.log.info("OP 1: Scraping Telegram Data (Task-1)")
    context.log.info("=" * 80)

    result = run_python_module(SCRAPER_MODULE, context)

    context.log.info("✅ Telegram scraping completed")
    return result


@op(
    description="Load raw JSON data from data lake into PostgreSQL (Task-2)",
    retry_policy=RetryPolicy(max_retries=2, delay=30),
    tags={"task": "task-2", "layer": "load"},
)
def load_raw_to_postgres(
    context: OpExecutionContext, scrape_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Op 2: Load raw Telegram JSON files into PostgreSQL raw schema.

    This op reads JSON files from data/raw/telegram_messages/ and loads
    them into PostgreSQL raw.telegram_messages table.

    Args:
        scrape_result: Result from scrape_telegram_data op

    Returns:
        Dictionary with loading statistics
    """
    context.log.info("=" * 80)
    context.log.info("OP 2: Loading Raw Data to PostgreSQL (Task-2)")
    context.log.info("=" * 80)

    result = run_python_script(LOAD_RAW_SCRIPT, context)

    context.log.info("✅ Raw data loading completed")
    return result


@op(
    description="Run dbt transformations to create star schema (Task-2)",
    retry_policy=RetryPolicy(max_retries=2, delay=30),
    tags={"task": "task-2", "layer": "transform"},
)
def run_dbt_transformations(
    context: OpExecutionContext, load_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Op 3: Run dbt models to transform raw data into star schema.

    This op executes dbt run to create:
    - staging.stg_telegram_messages
    - marts.dim_channels
    - marts.dim_dates
    - marts.fct_messages

    Args:
        load_result: Result from load_raw_to_postgres op

    Returns:
        Dictionary with dbt execution results
    """
    context.log.info("=" * 80)
    context.log.info("OP 3: Running dbt Transformations (Task-2)")
    context.log.info("=" * 80)

    # Run dbt models (staging + marts, excluding YOLO model)
    # Note: We run all models except fct_image_detections which depends on YOLO data
    result = run_dbt_command(
        "run", context, select="staging dim_channels dim_dates fct_messages"
    )

    # Run dbt tests
    context.log.info("Running dbt tests...")
    test_result = run_dbt_command(
        "test", context, select="staging dim_channels dim_dates fct_messages"
    )

    context.log.info("✅ dbt transformations completed")
    return {"run": result, "test": test_result}


@op(
    description="Run YOLO object detection on scraped images (Task-3)",
    retry_policy=RetryPolicy(max_retries=2, delay=60),
    tags={"task": "task-3", "layer": "enrich"},
)
def run_yolo_enrichment(
    context: OpExecutionContext, dbt_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Op 4: Run YOLO object detection on images from data lake.

    This op processes images in data/raw/images/ using YOLOv8 and
    generates detection results in data/processed/yolo_detections.csv.

    Args:
        dbt_result: Result from run_dbt_transformations op

    Returns:
        Dictionary with YOLO detection results
    """
    context.log.info("=" * 80)
    context.log.info("OP 4: Running YOLO Enrichment (Task-3)")
    context.log.info("=" * 80)

    result = run_python_module(YOLO_MODULE, context)

    context.log.info("✅ YOLO enrichment completed")
    return result


@op(
    description="Load YOLO detection results into PostgreSQL (Task-3)",
    retry_policy=RetryPolicy(max_retries=2, delay=30),
    tags={"task": "task-3", "layer": "load"},
)
def load_yolo_to_postgres(
    context: OpExecutionContext, yolo_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Op 5: Load YOLO detection CSV into PostgreSQL raw schema.

    This op reads data/processed/yolo_detections.csv and loads it
    into PostgreSQL raw.yolo_detections table.

    Args:
        yolo_result: Result from run_yolo_enrichment op

    Returns:
        Dictionary with loading statistics
    """
    context.log.info("=" * 80)
    context.log.info("OP 5: Loading YOLO Detections to PostgreSQL (Task-3)")
    context.log.info("=" * 80)

    result = run_python_script(LOAD_YOLO_SCRIPT, context)

    context.log.info("✅ YOLO detection loading completed")
    return result


@op(
    description="Run dbt model for YOLO image detections (Task-3)",
    retry_policy=RetryPolicy(max_retries=2, delay=30),
    tags={"task": "task-3", "layer": "transform"},
)
def run_dbt_yolo_model(
    context: OpExecutionContext, yolo_load_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Op 6: Run dbt model for YOLO image detections.

    This op executes dbt run --select fct_image_detections to create
    the enriched fact table with image detection data.

    Args:
        yolo_load_result: Result from load_yolo_to_postgres op

    Returns:
        Dictionary with dbt execution results
    """
    context.log.info("=" * 80)
    context.log.info("OP 6: Running dbt YOLO Model (Task-3)")
    context.log.info("=" * 80)

    # Run dbt model for image detections
    result = run_dbt_command("run", context, select="fct_image_detections")

    # Run dbt tests
    context.log.info("Running dbt tests for YOLO model...")
    test_result = run_dbt_command("test", context, select="fct_image_detections")

    context.log.info("✅ dbt YOLO model completed")
    return {"run": result, "test": test_result}


# ============================================================================
# Job Definition
# ============================================================================


@job(
    description="Complete Medical Telegram Warehouse Pipeline",
    tags={"pipeline": "medical-telegram-warehouse", "version": "1.0"},
)
def medical_telegram_warehouse_pipeline():
    """
    Main pipeline job that orchestrates all tasks in correct order.

    Pipeline DAG:
    1. scrape_telegram_data
    2. load_raw_to_postgres (depends on 1)
    3. run_dbt_transformations (depends on 2)
    4. run_yolo_enrichment (depends on 3)
    5. load_yolo_to_postgres (depends on 4)
    6. run_dbt_yolo_model (depends on 5)
    """
    # Task-1: Scrape Telegram
    scrape_result = scrape_telegram_data()

    # Task-2: Load raw data
    load_result = load_raw_to_postgres(scrape_result)

    # Task-2: Transform with dbt
    dbt_result = run_dbt_transformations(load_result)

    # Task-3: YOLO enrichment
    yolo_result = run_yolo_enrichment(dbt_result)

    # Task-3: Load YOLO results
    yolo_load_result = load_yolo_to_postgres(yolo_result)

    # Task-3: dbt YOLO model
    run_dbt_yolo_model(yolo_load_result)


# ============================================================================
# Scheduling
# ============================================================================


@schedule(
    job=medical_telegram_warehouse_pipeline,
    cron_schedule="0 2 * * *",  # Daily at 2:00 AM UTC
    default_status=DefaultSensorStatus.RUNNING,
    description="Daily pipeline execution at 2:00 AM UTC",
)
def daily_pipeline_schedule(context: ScheduleEvaluationContext):
    """
    Daily schedule for the complete pipeline.

    Runs every day at 2:00 AM UTC to:
    - Scrape latest Telegram messages
    - Load and transform data
    - Enrich with YOLO detections
    - Update analytical warehouse
    """
    return RunRequest(
        run_key=f"daily-pipeline-{context.scheduled_execution_time.strftime('%Y%m%d-%H%M%S')}",
        tags={
            "scheduled": "true",
            "schedule_type": "daily",
            "execution_time": context.scheduled_execution_time.isoformat(),
        },
    )
