{{ config(materialized='table') }}

with participation as (
    select match_id, team_1 as team_name, team_2 as opponent, match_winner
    from {{ ref('int_match_results') }}
    union all
    select match_id, team_2 as team_name, team_1 as opponent, match_winner
    from {{ ref('int_match_results') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['match_id', 'team_name']) }} as match_team_key,
    {{ dbt_utils.generate_surrogate_key(['match_id']) }} as match_key,
    {{ dbt_utils.generate_surrogate_key(['team_name']) }} as team_key,
    match_id,
    team_name,
    opponent,
    iff(match_winner = team_name, 1, 0) as is_win
from participation
