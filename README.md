# IPL Data Analysis

## Project Objective

IPL Data Analysis is an end-to-end data engineering and analytics project for collecting, preparing, modeling, and presenting Indian Premier League data. The project is being built in phases so that each layer can be tested and understood independently.

Phase 1 implements configurable Python ingestion into the local raw data lake, metadata capture, and basic raw-file validation. Phase 2 adds local Apache Airflow orchestration. Phase 3 loads validated raw files into Snowflake. Phase 4 transforms Snowflake raw data with dbt Core into analytics-ready models. Phase 5 adds dbt schema, relationship, freshness, and IPL business-rule tests. Phase 6 documents Power BI consumption, Phase 7 provides a Streamlit frontend, and Phase 8 adds safe, optional Terraform infrastructure.

## Architecture

```text
IPL Data Sources
        |
        v
Python Data Ingestion
        |
        v
Local Data Lake
        |
        v
Apache Airflow Orchestration
        |
        v
Snowflake Data Warehouse
        |
        v
dbt Transformations
        |
        v
dbt Data Quality Tests
        |
        v
Power BI Dashboard
        |
        v
Optional Streamlit Analytics Application
```

See [docs/architecture.md](docs/architecture.md) for the responsibilities and planned boundaries of each layer.

## Tech Stack

- **Python:** ingestion utilities, local data processing, and future automation code
- **Local data lake:** raw, external, and processed files under `data/`
- **Apache Airflow:** local workflow scheduling and orchestration
- **Snowflake:** raw data warehouse landing zone
- **dbt:** future SQL transformations and data quality tests
- **Power BI:** future business intelligence dashboard
- **Streamlit:** optional future interactive analytics application
- **Terraform:** optional infrastructure-as-code for future cloud extension

## Repository Structure

```text
.
|-- airflow/          # Airflow DAGs, Dockerfile, plugins, and local logs
|-- data/             # Local data lake zones
|-- docs/             # Architecture and project documentation
|-- ingestion/        # Configurable source extraction and raw-data validation
|-- powerbi/          # Future Power BI assets and notes
|-- quality/          # Future data quality checks
|-- scripts/          # Developer and operational helper scripts
|-- snowflake/        # Snowflake DDL and setup documentation
|-- dbt/              # dbt Core project and Snowflake analytics models
|-- streamlit_app/    # Optional future analytics application
|-- terraform/        # Optional Terraform infrastructure module
|-- tests/            # Automated tests
|-- transformations/  # Future dbt project
|-- .env.example      # Safe configuration template
|-- requirements.txt  # Python dependencies for this phase
`-- docker-compose.yml # Local Airflow and PostgreSQL services
```

## Local Python Environment

Create and activate a virtual environment from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then set `IPL_SOURCE_URLS` to a JSON object mapping dataset names such as `matches`, `deliveries`, `players`, and `teams` to CSV, JSON, or ZIP source URLs. Cricsheet's public IPL download is the documented source; additional datasets can be supplied by another compatible endpoint. The real `.env` file is ignored by Git.

Run ingestion and validation from the project root:

```powershell
python -m ingestion.fetch_ipl_data
python -m ingestion.validate_raw_data
pytest
```

Downloaded bytes are preserved in `data/raw/`; `ingestion_metadata.json` records each source, UTC ingestion timestamp, file name, and record count. Required columns can be configured with the `IPL_REQUIRED_COLUMNS` JSON mapping.

## Local Airflow

Copy `.env.example` to `.env` and set `IPL_SOURCE_URLS` before starting the stack. From the project root:

```powershell
docker compose up airflow-init
docker compose up -d airflow-webserver airflow-scheduler
```

Open the Airflow UI at [http://localhost:8080](http://localhost:8080) and sign in with `AIRFLOW_ADMIN_USERNAME` and `AIRFLOW_ADMIN_PASSWORD`. The `ipl_pipeline` DAG is paused and has no schedule by default, so trigger it manually from the DAG page. Set `IPL_AIRFLOW_SCHEDULE=@daily` in `.env` to enable scheduling.

Use the task log link in the UI to view logs, or inspect the mounted `airflow/logs/` directory. Stop the stack with:

```powershell
docker compose down
```

The DAG runs `start`, `ingest_data`, `validate_data`, `load_to_snowflake`, and `end` in order. The Snowflake load is isolated after validation so future warehouse or dbt work can extend the flow without changing ingestion.

## Snowflake Loading

Run [snowflake/01_setup.sql](snowflake/01_setup.sql) in Snowflake before enabling the load task. Copy the Snowflake settings in `.env.example` into `.env` and replace the account, user, password, and role values. The loader reads validated files from `data/raw/`, stores records as `VARIANT` in `IPL_ANALYTICS.RAW`, and logs counts in `RAW.INGESTION_METADATA`.

The Phase 3-5 DAG chain is `start → ingest_data → validate_data → load_to_snowflake → dbt_run → dbt_test → pipeline_success`. `validate_data` and `dbt_test` fail their tasks when quality checks fail. The Snowflake loader uses a SHA-256 file hash as its load key, so rerunning a DAG does not load the same file twice. dbt models use separate `STAGING`, `INTERMEDIATE`, and `ANALYTICS` schemas rather than changing the raw tables.

For trial accounts, use the XSMALL warehouse created by the setup script, keep `IPL_AIRFLOW_SCHEDULE` empty, and suspend the warehouse when testing is complete. The warehouse has auto-resume disabled and a 60-second auto-suspend setting. Load small fixtures first, run only when needed, and monitor credit usage in Snowsight. Detailed SQL and operating guidance are in [snowflake/README.md](snowflake/README.md).

## Streamlit Analytics App

The Phase 7 frontend reads only the dbt-generated Snowflake analytics marts. Install its isolated dependencies and configure credentials through environment variables or Streamlit secrets:

```powershell
python -m pip install -r streamlit_app/requirements.txt
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run streamlit_app/Home.py
```

Replace the example secret values before launching. The app opens at [http://localhost:8501](http://localhost:8501), caches Snowflake connections and read-only query results, and stops with a clear configuration error when credentials or permissions are missing. It uses the same `IPL_ANALYTICS.ANALYTICS` star schema described in [powerbi/dashboard_design.md](powerbi/dashboard_design.md).

## Terraform Infrastructure

Phase 8 is documented in [terraform/README.md](terraform/README.md). The default Terraform configuration provisions no cloud resources and keeps the local filesystem data lake as the development default. An optional private S3 data-lake bucket can be enabled explicitly with `enable_s3_data_lake = true`; review costs and the plan before applying.

## Future Phases

1. Implement source ingestion and store immutable files in the raw data zone. (Complete)
2. Add Airflow DAGs for scheduled ingestion and downstream dependencies. (Complete)
3. Add Snowflake connection and loading workflows. (Complete)
4. Initialize the dbt project with staging, intermediate, and mart models. (Complete)
5. Add dbt tests and broader data quality monitoring. (Complete)
6. Build the Power BI semantic model and dashboard. (Complete)
7. Add the optional Streamlit analytics experience. (Complete)
8. Add Terraform after the application architecture and cloud resources are stable. (Complete)
