from datetime import datetime

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator


def verify_environment():
    print("CivicPulse Airflow test passed.")
    print(f"Execution environment time: {datetime.now().isoformat()}")


with DAG(
    dag_id="civicpulse_test",
    description="Verify the CivicPulse Airflow environment",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["civicpulse", "setup"],
) as dag:
    verify_airflow = PythonOperator(
        task_id="verify_airflow",
        python_callable=verify_environment,
    )
