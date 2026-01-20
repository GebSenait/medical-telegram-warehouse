"""
Load YOLO Detection Results into PostgreSQL
Task-3: Data Enrichment - YOLO Detection Loading

This script reads YOLO detection CSV file and loads it into PostgreSQL
raw.yolo_detections table for dbt transformation.
"""

import csv
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
YOLO_OUTPUT_CSV = Path(
    os.getenv("YOLO_OUTPUT_CSV", "data/processed/yolo_detections.csv")
)

# PostgreSQL connection parameters
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "medical_warehouse")
POSTGRES_USER = os.getenv("POSTGRES_USER", "medical_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "medical_pass")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class YOLODetectionLoader:
    """Load YOLO detection CSV data into PostgreSQL raw schema."""

    def __init__(self):
        """Initialize the data loader."""
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish connection to PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
            )
            self.cursor = self.conn.cursor()
            logger.info(
                f"Connected to PostgreSQL: {POSTGRES_DB}@{POSTGRES_HOST}:{POSTGRES_PORT}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def create_raw_schema(self):
        """Create raw schema and yolo_detections table if they don't exist."""
        try:
            # Create raw schema
            self.cursor.execute("CREATE SCHEMA IF NOT EXISTS raw;")
            logger.info("Schema 'raw' created or already exists")

            # Create raw.yolo_detections table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS raw.yolo_detections (
                message_id BIGINT NOT NULL,
                channel_name VARCHAR(255) NOT NULL,
                image_path VARCHAR(500),
                detected_class VARCHAR(100),
                confidence_score NUMERIC(5, 4),
                image_category VARCHAR(50),
                num_detections INTEGER,
                loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (message_id, channel_name)
            );
            """
            self.cursor.execute(create_table_sql)
            self.conn.commit()
            logger.info("Table 'raw.yolo_detections' created or already exists")

            # Create indexes
            index_sql = """
            CREATE INDEX IF NOT EXISTS idx_yolo_detections_message_id
            ON raw.yolo_detections(message_id);

            CREATE INDEX IF NOT EXISTS idx_yolo_detections_channel_name
            ON raw.yolo_detections(channel_name);
            """
            self.cursor.execute(index_sql)
            self.conn.commit()
            logger.info("Indexes created or already exist")

        except Exception as e:
            logger.error(f"Error creating schema/table: {e}")
            self.conn.rollback()
            raise

    def load_csv(self, csv_path: Path) -> int:
        """
        Load YOLO detection CSV into PostgreSQL.

        Args:
            csv_path: Path to YOLO detection CSV file

        Returns:
            Number of rows loaded
        """
        if not csv_path.exists():
            logger.warning(f"YOLO detection CSV not found: {csv_path}")
            logger.info("Creating empty table structure. Run YOLO detection first.")
            return 0

        rows_loaded = 0
        rows_processed = 0

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Prepare data for bulk insert
                rows_to_insert = []

                for row in reader:
                    rows_processed += 1

                    try:
                        # Parse and validate data
                        message_id = (
                            int(row["message_id"]) if row.get("message_id") else None
                        )
                        channel_name = row.get("channel_name", "").strip()
                        image_path = row.get("image_path", "").strip()
                        detected_class = row.get("detected_class", "").strip() or None

                        # Parse confidence score
                        confidence_score = None
                        if row.get("confidence_score"):
                            try:
                                confidence_score = float(row["confidence_score"])
                            except (ValueError, TypeError):
                                confidence_score = None

                        image_category = row.get("image_category", "").strip() or None

                        # Parse num_detections
                        num_detections = None
                        if row.get("num_detections"):
                            try:
                                num_detections = int(row["num_detections"])
                            except (ValueError, TypeError):
                                num_detections = None

                        # Skip rows with missing required fields
                        if not message_id or not channel_name:
                            logger.warning(
                                f"Skipping row with missing message_id or channel_name: {row}"
                            )
                            continue

                        rows_to_insert.append(
                            (
                                message_id,
                                channel_name,
                                image_path or None,
                                detected_class,
                                confidence_score,
                                image_category,
                                num_detections,
                                datetime.now(),
                            )
                        )

                    except Exception as e:
                        logger.warning(f"Error processing row {rows_processed}: {e}")
                        continue

                # Bulk insert with upsert (ON CONFLICT UPDATE)
                if rows_to_insert:
                    insert_sql = """
                    INSERT INTO raw.yolo_detections
                    (message_id, channel_name, image_path, detected_class, confidence_score,
                     image_category, num_detections, loaded_at)
                    VALUES %s
                    ON CONFLICT (message_id, channel_name)
                    DO UPDATE SET
                        image_path = EXCLUDED.image_path,
                        detected_class = EXCLUDED.detected_class,
                        confidence_score = EXCLUDED.confidence_score,
                        image_category = EXCLUDED.image_category,
                        num_detections = EXCLUDED.num_detections,
                        loaded_at = EXCLUDED.loaded_at;
                    """

                    execute_values(
                        self.cursor,
                        insert_sql,
                        rows_to_insert,
                        template=None,
                        page_size=1000,
                    )

                    rows_loaded = self.cursor.rowcount
                    self.conn.commit()
                    logger.info(f"Loaded {rows_loaded} rows into raw.yolo_detections")
                else:
                    logger.warning("No valid rows to insert")

        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            self.conn.rollback()
            raise

        return rows_loaded

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point for YOLO detection loader."""
    logger.info("=" * 60)
    logger.info("YOLO Detection Loader - Task-3")
    logger.info("=" * 60)

    loader = YOLODetectionLoader()

    try:
        # Connect to database
        if not loader.connect():
            logger.error("Failed to connect to PostgreSQL")
            sys.exit(1)

        # Create schema and table
        loader.create_raw_schema()

        # Load CSV
        rows_loaded = loader.load_csv(YOLO_OUTPUT_CSV)

        logger.info("=" * 60)
        logger.info(f"YOLO detection loading complete. Rows loaded: {rows_loaded}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        loader.close()


if __name__ == "__main__":
    main()
