import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
PAGE_SIZE = 5_000
WINDOW_DAYS = 30

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "nyc_311_backfill_30d.jsonl"


def create_session():
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update(
        {"User-Agent": "CivicPulse-Portfolio-Project/1.0"}
    )
    return session


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Refuse to overwrite an existing backfill file accidentally.
    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"{OUTPUT_FILE} already exists. Rename or remove it "
            "before intentionally running a fresh backfill."
        )

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=WINDOW_DAYS)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total = 0
    session = create_session()

    with OUTPUT_FILE.open("x", encoding="utf-8") as output:
        day_start = start

        while day_start < now:
            day_end = min(
                day_start + timedelta(days=1),
                now,
            )

            start_string = day_start.strftime("%Y-%m-%dT%H:%M:%S")
            end_string = day_end.strftime("%Y-%m-%dT%H:%M:%S")

            where_clause = (
                f"created_date >= '{start_string}' "
                f"AND created_date < '{end_string}'"
            )

            offset = 0
            daily_total = 0

            while True:
                params = {
                    "$where": where_clause,
                    "$order": "created_date ASC, unique_key ASC",
                    "$limit": PAGE_SIZE,
                    "$offset": offset,
                }

                response = session.get(
                    API_URL,
                    params=params,
                    timeout=(10, 90),
                )
                response.raise_for_status()
                records = response.json()

                if not isinstance(records, list):
                    raise ValueError(
                        "Expected the API to return a JSON array."
                    )

                if not records:
                    break

                for record in records:
                    output.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )

                count = len(records)
                total += count
                daily_total += count
                offset += count

                if count < PAGE_SIZE:
                    break

                time.sleep(0.2)

            output.flush()

            print(
                f"{day_start.date()}: "
                f"{daily_total:,} records; "
                f"{total:,} total"
            )

            day_start = day_end

            # Pause between daily partitions.
            time.sleep(0.2)

    print(f"\nBackfill saved to: {OUTPUT_FILE}")
    print(f"Total records downloaded: {total:,}")
    print(
        "The original nyc_311_requests.jsonl file "
        "was not modified."
    )


if __name__ == "__main__":
    main()
