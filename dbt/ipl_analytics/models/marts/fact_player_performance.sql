{{ config(materialized='table') }}

select
    {{ dbt_utils.generate_surrogate_key(['performance.match_id', 'performance.player_name']) }} as performance_key,
    {{ dbt_utils.generate_surrogate_key(['performance.match_id']) }} as match_key,
    {{ dbt_utils.generate_surrogate_key(['performance.player_name']) }} as player_key,
    performance.match_id,
    performance.player_name,
    performance.runs_scored,
    performance.balls_faced,
    performance.fours,
    performance.sixes,
    performance.wickets,
    performance.runs_conceded,
    performance.balls_bowled,
    performance.strike_rate,
    performance.bowling_average
from {{ ref('int_player_match_performance') }} performance
