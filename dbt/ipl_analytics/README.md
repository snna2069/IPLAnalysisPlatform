# IPL Analytics dbt Project

This dbt Core project transforms `IPL_ANALYTICS.RAW` source tables into staging views, intermediate cricket calculations, and analytics star-schema tables.

Run from the repository root after the Snowflake setup script and `.env` configuration:

```powershell
python -m pip install -r requirements.txt
cd dbt/ipl_analytics
dbt deps
dbt debug --profiles-dir .
dbt run --profiles-dir .
dbt source freshness --profiles-dir .
dbt test --profiles-dir . --store-failures
```

Credentials are read from environment variables through `profiles.yml`; no secrets belong in this directory. The custom schema macro keeps staging, intermediate, and analytics models in `IPL_ANALYTICS.STAGING`, `IPL_ANALYTICS.INTERMEDIATE`, and `IPL_ANALYTICS.ANALYTICS` respectively.

Quality checks are defined in `models/schema.yml` and `tests/`. They cover primary keys, nullability, accepted toss decisions, fact-to-dimension relationships, source freshness, non-negative cricket metrics, valid seasons, valid teams, and delivery ownership. Freshness failures and dbt tests both stop the Airflow pipeline at `dbt_test`.
