# IPL Analytics dbt Project

This dbt Core project transforms `IPL_ANALYTICS.RAW` source tables into staging views, intermediate cricket calculations, and analytics star-schema tables.

Run from the repository root after the Snowflake setup script and `.env` configuration:

```powershell
python -m pip install -r requirements.txt
cd dbt/ipl_analytics
dbt deps
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

Credentials are read from environment variables through `profiles.yml`; no secrets belong in this directory. The custom schema macro keeps staging, intermediate, and analytics models in `IPL_ANALYTICS.STAGING`, `IPL_ANALYTICS.INTERMEDIATE`, and `IPL_ANALYTICS.ANALYTICS` respectively.
