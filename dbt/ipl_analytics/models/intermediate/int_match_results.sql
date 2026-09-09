{{ config(materialized='table') }}

select
    match_id,
    season,
    match_date,
    venue,
    team_1,
    team_2,
    toss_winner,
    toss_decision,
    winner,
    result_type,
    coalesce(win_by_runs, 0) as win_by_runs,
    coalesce(win_by_wickets, 0) as win_by_wickets,
    iff(winner is not null and winner = team_1, team_1, team_2) as winner_side,
    source_file,
    file_hash,
    loaded_at
from {{ ref('stg_matches') }}
