import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
PAGE_SIZE = 5000
LOOKBACK_DAYS = 3
OUTPUT_FILE = Path("/tmp/civicpulse_311_incremental.jsonl")


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
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {"User-Agent": "CivicPulse-Portfolio-Project/1.0"}
    )
    return session


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    cutoff_string = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    total = 0
    offset = 0
    session = create_session()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as output:
        while True:
            params = {
                "$where": f"created_date >= '{cutoff_string}'",
                "$order": "created_date ASC, unique_key ASC",
                "$limit": PAGE_SIZE,
                "$offset": offset,
            }

            response = session.get(API_URL, params=params, timeout=(10, 90))
            response.raise_for_status()
            records = response.json()

            if not isinstance(records, list):
                raise ValueError("Expected the API to return a JSON array.")

            if not records:
                break

            for record in records:
                if not record.get("unique_key") or not record.get("created_date"):
                    raise ValueError("API returned a record missing required fields.")
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

            total += len(records)
            offset += len(records)
            print(f"Downloaded {total:,} records")

            if len(records) < PAGE_SIZE:
                break

            time.sleep(0.2)

    print(f"Incremental extraction complete: {total:,} records")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
