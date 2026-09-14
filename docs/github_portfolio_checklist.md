# GitHub Portfolio Checklist

Use this checklist before publishing the IPL Data Analysis project.

## Repository hygiene

- [ ] No `.env`, Streamlit secrets, Snowflake passwords, AWS keys, PBIX credentials, or Terraform state is committed.
- [ ] `terraform.tfvars`, Terraform plans, dbt targets, Airflow logs, and local data files are ignored.
- [ ] `.env.example` and `.streamlit/secrets.toml.example` contain placeholders only.
- [ ] README commands match the current repository structure.

## Technical evidence

- [ ] `pytest` passes.
- [ ] Python sources and the Airflow DAG compile/import successfully.
- [ ] `dbt deps` and `dbt parse` pass with non-production placeholder credentials.
- [ ] `dbt source freshness` and `dbt test` have recent successful evidence from Snowflake.
- [ ] `terraform fmt`, `terraform validate`, and `terraform plan` pass with S3 disabled.
- [ ] Docker Compose configuration renders successfully.

## Portfolio narrative

- [ ] README architecture diagram shows ingestion, lake, validation, Airflow, Snowflake, dbt, quality, and consumers.
- [ ] [docs/data_dictionary.md](data_dictionary.md) explains mart grain and column meaning.
- [ ] [powerbi/dashboard_design.md](../powerbi/dashboard_design.md) explains the semantic model and KPI design.
- [ ] Screenshots show the Airflow graph, dbt quality evidence, Snowflake layers, and analytics consumers.
- [ ] README explains what is intentionally not implemented, especially dbt vs Power BI boundaries.
- [ ] A short project summary names the engineering decisions, failure handling, idempotency, and cost controls.

## Demo readiness

- [ ] A reviewer can install dependencies without private files.
- [ ] A reviewer can see how to run ingestion-only, Airflow, dbt, Streamlit, and Terraform validation.
- [ ] Snowflake and AWS trial-credit safeguards are documented.
- [ ] Demo credentials use a least-privilege, read-only consumer role where possible.