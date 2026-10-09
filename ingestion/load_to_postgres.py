import json
import os
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
    closed_date = EXCLUDED.closed_date,
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
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {DATA_FILE}. Run the extraction script first."
        )

    batch = []
    processed = 0

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
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

                    if len(batch) >= 1000:
                        cur.executemany(UPSERT_SQL, batch)
                        processed += len(batch)
                        print(f"Processed {processed:,} records")
                        batch.clear()

                if batch:
                    cur.executemany(UPSERT_SQL, batch)
                    processed += len(batch)

    print(f"Finished loading {processed:,} records into raw.nyc_311_requests.")


if __name__ == "__main__":
    main()
