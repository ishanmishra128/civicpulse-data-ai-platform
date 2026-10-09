import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
PAGE_SIZE = 5_000
MAX_RECORDS = 50_000
WINDOW_DAYS = 180

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "nyc_311_requests.jsonl"

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
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update(
        {"User-Agent": "CivicPulse-Portfolio-Project/1.0"}
    )
    return session

def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    cutoff_string = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    offset = 0
    session = create_session()

    with OUTPUT_FILE.open("w", encoding="utf-8") as output:
        while total < MAX_RECORDS:
            limit = min(PAGE_SIZE, MAX_RECORDS - total)

            params = {
                "$where": f"created_date >= '{cutoff_string}'",
                "$order": "created_date DESC, unique_key ASC",
                "$limit": limit,
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
                raise ValueError("Expected the API to return a JSON array.")

            if not records:
                break

            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

            total += len(records)
            offset += len(records)

            print(f"Downloaded {total:,} records")

            if len(records) < limit:
                break

            # Avoid making unnecessary rapid requests.
            time.sleep(0.2)

    print(f"\nSaved raw records to: {OUTPUT_FILE}")
    print(f"Total records: {total:,}")

    if total == MAX_RECORDS:
        print("Sample cap reached; more records may be available.")

    inspect_sample(OUTPUT_FILE)


def inspect_sample(path):
    required_fields = [
        "unique_key",
        "created_date",
        "closed_date",
        "complaint_type",
        "agency",
        "borough",
    ]

    counts = {field: 0 for field in required_fields}
    missing = {field: 0 for field in required_fields}
    invalid_created_dates = 0
    duplicate_keys = 0
    seen_keys = set()
    row_count = 0

    with path.open("r", encoding="utf-8") as source:
        for line in source:
            record = json.loads(line)
            row_count += 1

            for field in required_fields:
                value = record.get(field)
                if value is None or value == "":
                    missing[field] += 1
                else:
                    counts[field] += 1

            key = record.get("unique_key")
            if key is not None:
                if key in seen_keys:
                    duplicate_keys += 1
                seen_keys.add(key)

            created = record.get("created_date")
            if created:
                try:
                    datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    invalid_created_dates += 1

    print("\n--- Data quality inspection ---")
    print(f"Rows inspected: {row_count:,}")
    print(f"Distinct source keys: {len(seen_keys):,}")
    print(f"Duplicate source keys: {duplicate_keys:,}")
    print(f"Invalid creation timestamps: {invalid_created_dates:,}")

    print("\nField completeness:")
    for field in required_fields:
        print(
            f"  {field}: {counts[field]:,} present; "
            f"{missing[field]:,} missing"
        )


if __name__ == "__main__":
    main()    