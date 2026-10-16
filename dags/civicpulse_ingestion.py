
import os
import subprocess
import sys
from datetime import datetime, timedelta

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator

INGESTION_DIR = "/opt/civicpulse/ingestion"
DBT_DIR = "/opt/civicpulse/civicpulse_dbt"
DBT_BIN = "/home/airflow/dbt-venv/bin/dbt"
DBT_PROFILES_DIR = "/opt/airflow/config/dbt"

sys.path.insert(0, INGESTION_DIR)

import incremental_extract
import load_to_postgres


def extract_incremental():
    metrics = incremental_extract.main()
    print(f"Extraction metrics: {metrics}")
    return metrics


def load_incremental():
    load_to_postgres.DATA_FILE = incremental_extract.OUTPUT_FILE
    metrics = load_to_postgres.main()
    print(f"Load metrics: {metrics}")
    return metrics


def run_dbt(command):
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = DBT_PROFILES_DIR

    subprocess.run(
        [
            DBT_BIN,
            command,
            "--project-dir",
            DBT_DIR,
            "--profiles-dir",
            DBT_PROFILES_DIR,
            "--log-path",
            "/tmp/dbt-logs",
            "--target-path",
            "/tmp/dbt-target",
        ],
        cwd=DBT_DIR,
        env=env,
        check=True,
    )


def dbt_run():
    run_dbt("run")


def dbt_test():
    run_dbt("test")


with DAG(
    dag_id="civicpulse_ingestion",
    description="Ingest NYC 311 requests, build dbt models, and test data quality",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",
    catchup=False,
    default_args={
        "owner": "civicpulse",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["civicpulse", "ingestion", "dbt"],
) as dag:
    extract_nyc_311 = PythonOperator(
        task_id="extract_nyc_311",
        python_callable=extract_incremental,
    )

    load_nyc_311 = PythonOperator(
        task_id="load_nyc_311",
        python_callable=load_incremental,
    )

    dbt_run_task = PythonOperator(
        task_id="dbt_run",
        python_callable=dbt_run,
    )

    dbt_test_task = PythonOperator(
        task_id="dbt_test",
        python_callable=dbt_test,
    )

    extract_nyc_311 >> load_nyc_311 >> dbt_run_task >> dbt_test_task
