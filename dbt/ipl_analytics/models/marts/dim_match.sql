{{ config(materialized='table') }}

select
    {{ dbt_utils.generate_surrogate_key(['match_id']) }} as match_key,
    match_id,
    {{ dbt_utils.generate_surrogate_key(['season']) }} as season_key,
    {{ dbt_utils.generate_surrogate_key(['venue']) }} as venue_key,
    {{ dbt_utils.generate_surrogate_key(['team_1']) }} as team_1_key,
    {{ dbt_utils.generate_surrogate_key(['team_2']) }} as team_2_key,
    match_date,
    season,
    venue,
    team_1,
    team_2,
    toss_winner,
    toss_decision,
    winner,
    result_type,
    win_by_runs,
    win_by_wickets,
    source_file,
    loaded_at
from {{ ref('int_match_results') }}
