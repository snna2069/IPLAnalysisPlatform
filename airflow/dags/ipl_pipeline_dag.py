"""Airflow orchestration for the local IPL ingestion pipeline."""

from __future__ import annotations

import os
from datetime import timedelta

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from pendulum import datetime

from ingestion.fetch_ipl_data import ingest
from ingestion.load_to_snowflake import load_to_snowflake
from ingestion.validate_raw_data import validate_raw_data


def validate_data() -> None:
    """Fail the DAG when any raw file does not pass validation."""
    results = validate_raw_data()
    errors = {path: file_errors for path, file_errors in results.items() if file_errors}
    if errors:
        raise AirflowException(f"Raw data validation failed: {errors}")


with DAG(
    dag_id="ipl_pipeline",
    description="Ingest, validate, and load IPL data into Snowflake raw tables",
    start_date=datetime(2026, 1, 1, tz="UTC"),
    schedule=os.getenv("IPL_AIRFLOW_SCHEDULE") or None,
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "ipl-data-platform",
        "depends_on_past": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["ipl", "phase-3", "snowflake", "raw"],
) as dag:
    start = EmptyOperator(task_id="start")

    ingest_data = PythonOperator(
        task_id="ingest_data",
        python_callable=ingest,
        doc="Download configured IPL sources into data/raw and write ingestion metadata.",
    )

    validate_data_task = PythonOperator(
        task_id="validate_data",
        python_callable=validate_data,
        doc="Check raw files for presence, records, required columns, and duplicates.",
    )

    load_to_snowflake_task = PythonOperator(
        task_id="load_to_snowflake",
        python_callable=load_to_snowflake,
        doc="Load validated raw files once into Snowflake RAW tables.",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/airflow/project/dbt/ipl_analytics && "
            "dbt deps --profiles-dir . && "
            "dbt build --profiles-dir ."
        ),
        append_env=True,
        doc="Build dbt staging, intermediate, and analytics models in Snowflake.",
    )

    end = EmptyOperator(task_id="end")

    start >> ingest_data >> validate_data_task >> load_to_snowflake_task >> dbt_run >> end