# Phase 5 Quality Tests

Schema tests in `models/schema.yml` protect model contracts:

- `not_null` and `unique` protect dimension and fact keys.
- `accepted_values` constrains toss decisions to `bat` or `field`.
- `relationships` checks fact-to-dimension and delivery-to-match references.
- `dbt_utils.expression_is_true` protects non-negative runs, wickets, and total-runs arithmetic.

Singular SQL tests in this directory protect IPL-specific business rules:

- Every match resolves to a valid season.
- Every delivery resolves to an existing match.
- Match team and winner references resolve to `dim_team`.
- Player performance values cannot be negative.
- A match cannot list the same team twice.

A dbt test passes when its SQL returns zero rows. Airflow runs these tests after `dbt_run`; any non-zero result causes the `dbt_test` task and pipeline to fail, with the failing SQL and rows available in task logs and dbt artifacts.
