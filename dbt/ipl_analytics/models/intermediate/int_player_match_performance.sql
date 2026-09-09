{{ config(materialized='table') }}

with batting as (
    select
        match_id,
        batter as player_name,
        sum(batter_runs) as runs_scored,
        count(*) as balls_faced,
        sum(is_four) as fours,
        sum(is_six) as sixes,
        0 as wickets,
        0 as runs_conceded,
        0 as balls_bowled
    from {{ ref('int_match_deliveries') }}
    group by match_id, batter
),
bowling as (
    select
        match_id,
        bowler as player_name,
        0 as runs_scored,
        0 as balls_faced,
        0 as fours,
        0 as sixes,
        sum(is_wicket) as wickets,
        sum(total_runs) as runs_conceded,
        count_if(is_illegal_delivery = 0) as balls_bowled
    from {{ ref('int_match_deliveries') }}
    group by match_id, bowler
)
select
    match_id,
    player_name,
    sum(runs_scored) as runs_scored,
    sum(balls_faced) as balls_faced,
    sum(fours) as fours,
    sum(sixes) as sixes,
    sum(wickets) as wickets,
    sum(runs_conceded) as runs_conceded,
    sum(balls_bowled) as balls_bowled,
    iff(sum(balls_faced) > 0, round(sum(runs_scored) / sum(balls_faced) * 100, 2), 0) as strike_rate,
    iff(sum(wickets) > 0, round(sum(runs_conceded) / nullif(sum(wickets), 0), 2), null) as bowling_average
from (
    select * from batting
    union all
    select * from bowling
)
group by match_id, player_name
