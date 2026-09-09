# Snowflake Phase 3 Setup

Run `01_setup.sql` once in a Snowflake worksheet using an administrative role. It creates the `IPL_ANALYTICS` database, an XSMALL warehouse, separate `RAW` and `ANALYTICS` schemas, four raw tables, and the `RAW.INGESTION_METADATA` load ledger.

The loader stores each source record in `RAW_PAYLOAD` as Snowflake `VARIANT` and keeps the source file and SHA-256 hash alongside it. The analytics schema is intentionally empty; dbt and modeled tables belong to a later phase.

The warehouse is configured with `AUTO_SUSPEND = 60`, `AUTO_RESUME = FALSE`, and `INITIALLY_SUSPENDED = TRUE`. Start it only while loading:

```sql
ALTER WAREHOUSE IPL_ANALYTICS_WH RESUME;
ALTER WAREHOUSE IPL_ANALYTICS_WH SUSPEND;
```

To protect trial credits, use XSMALL, keep auto-resume disabled, suspend the warehouse after a run, and avoid leaving Airflow scheduled continuously. Load only the files needed for testing and monitor usage in Snowsight. Never commit `.env` or credentials.