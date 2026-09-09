"""Airflow orchestration for the local IPL ingestion pipeline."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from pendulum import datetime

from ingestion.fetch_ipl_data import ingest
from ingestion.validate_raw_data import validate_raw_data


def prepare_data_for_warehouse() -> None:
    """Create the warehouse handoff directory without transforming raw data."""
    processed_dir = Path(os.getenv("IPL_PROCESSED_DIR", "/opt/airflow/project/data/processed"))
    processed_dir.mkdir(parents=True, exist_ok=True)


with DAG(
    dag_id="ipl_pipeline",
    description="Ingest and validate IPL data before the future warehouse load",
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
    tags=["ipl", "phase-2", "local-data-lake"],
) as dag:
    start = EmptyOperator(task_id="start")

    ingest_ipl_data = PythonOperator(
        task_id="ingest_ipl_data",
        python_callable=ingest,
        doc="Download configured IPL sources into data/raw and write ingestion metadata.",
    )

    validate_raw_data_task = PythonOperator(
        task_id="validate_raw_data",
        python_callable=validate_raw_data,
        doc="Check raw files for presence, records, required columns, and duplicates.",
    )

    prepare_data_for_warehouse_task = PythonOperator(
        task_id="prepare_data_for_warehouse",
        python_callable=prepare_data_for_warehouse,
        doc="Prepare the local warehouse handoff boundary; no transformation is performed yet.",
    )

    end = EmptyOperator(task_id="end")

    start >> ingest_ipl_data >> validate_raw_data_task >> prepare_data_for_warehouse_task >> end