# IPL Data Analysis Architecture

## Purpose

This document defines the boundaries for the IPL Data Analysis platform. Phases 1-5 implement ingestion, orchestration, Snowflake loading, dbt analytics modeling, and dbt quality checks. Phase 6 documents Power BI consumption, Phase 7 provides Streamlit consumption, and Phase 8 adds optional Terraform infrastructure.

## Data Flow

```text
Source APIs or files
        |
        v
Python ingestion layer
        |
        v
Local data lake: raw -> processed
        |
        v
Airflow orchestration
        |
        v
Snowflake warehouse: landing -> analytics
        |
        v
dbt models and tests
        |
        +--> Power BI dashboard
        |
        `--> Optional Streamlit application
```

## Layer Responsibilities

### 1. IPL Data Sources

External APIs, downloadable files, or other trusted IPL data providers are the system inputs. Source details and access patterns will be documented when ingestion is implemented.

### 2. Python Data Ingestion

Python code will retrieve source data, validate basic availability, preserve source extracts, and write reproducible outputs. Ingestion should be rerunnable and should not mutate previously captured raw files.

### 3. Local Data Lake

The `data/` directory is divided into zones:

- `data/raw/`: immutable source extracts
- `data/external/`: manually supplied or third-party reference files
- `data/processed/`: cleaned files ready for warehouse loading

Local data is ignored by Git because it can be large, sensitive, or reproducible from source systems.

### 4. Apache Airflow

Airflow coordinates the Phase 1 ingestion and validation tasks through `airflow/dags/ipl_pipeline_dag.py`. The local Docker Compose stack mounts DAGs, plugins, logs, the Python source tree, and data lake directories. The DAG includes a warehouse handoff task so a future Snowflake load can be inserted without redesigning the upstream flow.

### 5. Snowflake

Snowflake provides the warehouse landing zone. `IPL_ANALYTICS.RAW` contains source-shaped `VARIANT` records and an ingestion metadata ledger keyed by file hash. `IPL_ANALYTICS.ANALYTICS` is reserved for future modeled data. Credentials are supplied through environment variables or a managed secret mechanism; no credentials are stored in source code.

### 6. dbt

The `dbt/ipl_analytics/` project contains source definitions, staging views, intermediate cricket calculations, dimensional models, fact models, documentation, and schema/singular tests. `dbt run` and then `dbt test` run after the Snowflake raw load in Airflow. Test failures stop the pipeline before `pipeline_success`. dbt build artifacts and local credential profiles are excluded from Git.

### 7. Consumption

Power BI will provide the primary dashboard experience. Streamlit is an optional Python-based application for exploratory or self-service analysis. Both consumers should read curated analytical models rather than raw source files.

### 8. Terraform

Terraform provides an optional, disabled-by-default AWS S3 data-lake module. Local filesystem storage remains the development default. State files, variable files, plans, and provider caches are excluded from Git; remote encrypted state and additional cloud resources can be added later without changing application code.

## Configuration Principles

- Store secret values in a local `.env` file or a managed secret store; never commit them.
- Keep raw source data reproducible and separate from transformed outputs.
- Pin or constrain dependencies in `requirements.txt` and add phase-specific packages only when they are needed.
- Keep orchestration, transformation, quality, and presentation concerns in their own directories.
- Add automated tests alongside each implementation phase.
