import sys
from datetime import datetime, timedelta

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator

INGESTION_DIR = "/opt/civicpulse/ingestion"
sys.path.insert(0, INGESTION_DIR)

import incremental_extract
import load_to_postgres


def extract_incremental():
    incremental_extract.main()


def load_incremental():
    load_to_postgres.DATA_FILE = incremental_extract.OUTPUT_FILE
    load_to_postgres.main()


with DAG(
    dag_id="civicpulse_ingestion",
    description="Incrementally ingest NYC 311 requests into PostgreSQL",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",
    catchup=False,
    default_args={
        "owner": "civicpulse",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["civicpulse", "ingestion"],
) as dag:
    extract_nyc_311 = PythonOperator(
        task_id="extract_nyc_311",
        python_callable=extract_incremental,
    )

    load_nyc_311 = PythonOperator(
        task_id="load_nyc_311",
        python_callable=load_incremental,
    )

    extract_nyc_311 >> load_nyc_311
