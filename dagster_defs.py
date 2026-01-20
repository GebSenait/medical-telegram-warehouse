"""
Dagster Definitions for Medical Telegram Warehouse Pipeline
Task-5: Production-Grade Pipeline Orchestration

This module exports Dagster definitions for the webserver.
"""

from dagster import Definitions
from pipeline import medical_telegram_warehouse_pipeline, daily_pipeline_schedule

defs = Definitions(
    jobs=[medical_telegram_warehouse_pipeline],
    schedules=[daily_pipeline_schedule],
)
