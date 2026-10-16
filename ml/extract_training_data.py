
import os

import pandas as pd
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://civicpulse:civicpulse_local_dev@localhost:5050/civicpulse",
)

QUERY = """
SELECT
    unique_key,
    created_date,
    complaint_type,
    agency,
    borough,
    EXTRACT(HOUR FROM created_date)::INTEGER AS created_hour,
    EXTRACT(ISODOW FROM created_date)::INTEGER AS created_day_of_week,
    EXTRACT(MONTH FROM created_date)::INTEGER AS created_month,
    closure_hours
FROM analytics_analytics.fct_311_closure_performance
WHERE created_date IS NOT NULL
  AND complaint_type IS NOT NULL
  AND agency IS NOT NULL
  AND borough IS NOT NULL
  AND closure_hours IS NOT NULL
  AND closure_hours >= 0
ORDER BY created_date ASC, unique_key ASC
"""


def extract_training_data(output_path="data/processed/311_training_data.parquet"):
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as connection:
            df = pd.read_sql_query(text(QUERY), connection)
    finally:
        engine.dispose()

    if df.empty:
        raise ValueError("No eligible training records found.")

    df["created_date"] = pd.to_datetime(df["created_date"], utc=True)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_parquet(output_path, index=False)

    print(f"Saved {len(df):,} records to {output_path}")
    print(f"Date range: {df['created_date'].min()} to {df['created_date'].max()}")
    print(f"Missing values:\n{df.isna().sum().to_string()}")
    print(f"Target summary:\n{df['closure_hours'].describe().to_string()}")

    return df


if __name__ == "__main__":
    extract_training_data()



