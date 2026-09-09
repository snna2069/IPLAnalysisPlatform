# IPL Data Analysis

## Project Objective

IPL Data Analysis is an end-to-end data engineering and analytics project for collecting, preparing, modeling, and presenting Indian Premier League data. The project is being built in phases so that each layer can be tested and understood independently.

Phase 1 implements configurable Python ingestion into the local raw data lake, metadata capture, and basic raw-file validation. Orchestration, warehouse, transformation, quality, dashboard, and application implementation remain future phases.

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
- **Apache Airflow:** future workflow scheduling and orchestration
- **Snowflake:** future cloud data warehouse
- **dbt:** future SQL transformations and data quality tests
- **Power BI:** future business intelligence dashboard
- **Streamlit:** optional future interactive analytics application
- **Terraform:** future infrastructure-as-code layer

## Repository Structure

```text
.
|-- airflow/          # Future DAGs, plugins, and local Airflow logs
|-- data/             # Local data lake zones
|-- docs/             # Architecture and project documentation
|-- ingestion/        # Configurable source extraction and raw-data validation
|-- powerbi/          # Future Power BI assets and notes
|-- quality/          # Future data quality checks
|-- scripts/          # Developer and operational helper scripts
|-- streamlit_app/    # Optional future analytics application
|-- terraform/        # Future infrastructure-as-code
|-- tests/            # Automated tests
|-- transformations/  # Future dbt project
|-- .env.example      # Safe configuration template
|-- requirements.txt  # Python dependencies for this phase
`-- docker-compose.yml # Reserved for future local services
```

## Local Python Environment

Create and activate a virtual environment from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then set `IPL_SOURCE_URLS` to a JSON object mapping dataset names such as `matches`, `deliveries`, `players`, and `teams` to CSV or JSON source URLs. Cricsheet's public IPL download is the documented source; additional datasets can be supplied by another compatible endpoint. The real `.env` file is ignored by Git.

Run ingestion and validation from the project root:

```powershell
python -m ingestion.fetch_ipl_data
python -m ingestion.validate_raw_data
pytest
```

Downloaded bytes are preserved in `data/raw/`; `ingestion_metadata.json` records each source, UTC ingestion timestamp, file name, and record count. Required columns can be configured with the `IPL_REQUIRED_COLUMNS` JSON mapping.

## Future Phases

1. Implement source ingestion and store immutable files in the raw data zone.
2. Add Airflow DAGs for scheduled ingestion and downstream dependencies.
3. Add Snowflake connection and loading workflows.
4. Initialize the dbt project with staging, intermediate, and mart models.
5. Add dbt tests and broader data quality monitoring.
6. Build the Power BI semantic model and dashboard.
7. Add the optional Streamlit analytics experience.
8. Add Terraform after the application architecture and cloud resources are stable.
