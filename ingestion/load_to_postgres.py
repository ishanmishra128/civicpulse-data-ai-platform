import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = Path(
    os.getenv(
        "CIVICPULSE_DATA_FILE",
        str(PROJECT_ROOT / "data" / "raw" / "nyc_311_requests.jsonl"),
    )
)
if not DATA_FILE.is_absolute():
    DATA_FILE = PROJECT_ROOT / DATA_FILE

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5050")),
    "dbname": os.getenv("PGDATABASE", "civicpulse"),
    "user": os.getenv("PGUSER", "civicpulse"),
    "password": os.getenv("PGPASSWORD", "civicpulse_local_dev"),
}

BATCH_SIZE = 1000

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

UPSERT_SQL = """
INSERT INTO raw.nyc_311_requests (
    unique_key,
    created_date,
    closed_date,
    complaint_type,
    agency,
    borough,
    raw_record
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (unique_key) DO UPDATE SET
    created_date = EXCLUDED.created_date,
    closed_date = COALESCE(EXCLUDED.closed_date, raw.nyc_311_requests.closed_date),
    complaint_type = EXCLUDED.complaint_type,
    agency = EXCLUDED.agency,
    borough = EXCLUDED.borough,
    raw_record = EXCLUDED.raw_record,
    loaded_at = NOW();
"""


def parse_timestamp(value):
    if not value:
        return None

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    started = time.perf_counter()
    processed = 0
    batches = 0

    logger.info("Starting PostgreSQL load from %s", DATA_FILE)

    try:
        if not DATA_FILE.exists():
            raise FileNotFoundError(
                f"Could not find {DATA_FILE}. Run the extraction script first."
            )

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                batch = []

                with DATA_FILE.open("r", encoding="utf-8") as file:
                    for line_number, line in enumerate(file, start=1):
                        if not line.strip():
                            continue

                        record = json.loads(line)
                        unique_key = record.get("unique_key")
                        created_date = parse_timestamp(record.get("created_date"))

                        if not unique_key or not created_date:
                            raise ValueError(
                                f"Missing unique_key or created_date on line {line_number}"
                            )

                        batch.append(
                            (
                                unique_key,
                                created_date,
                                parse_timestamp(record.get("closed_date")),
                                record.get("complaint_type"),
                                record.get("agency"),
                                record.get("borough"),
                                Jsonb(record),
                            )
                        )

                        if len(batch) >= BATCH_SIZE:
                            cur.executemany(UPSERT_SQL, batch)
                            processed += len(batch)
                            batches += 1
                            logger.info(
                                "Upserted %s records across %s batches",
                                processed,
                                batches,
                            )
                            batch.clear()

                    if batch:
                        cur.executemany(UPSERT_SQL, batch)
                        processed += len(batch)
                        batches += 1

        elapsed = time.perf_counter() - started
        logger.info(
            "Load completed: records_upserted=%s batches=%s duration_seconds=%.2f",
            processed,
            batches,
            elapsed,
        )

        return {
            "records_upserted": processed,
            "batches": batches,
            "duration_seconds": round(elapsed, 2),
            "status": "success",
        }

    except Exception:
        elapsed = time.perf_counter() - started
        logger.exception(
            "Load failed: records_processed_before_failure=%s duration_seconds=%.2f",
            processed,
            elapsed,
        )
        raise


if __name__ == "__main__":
    main()
