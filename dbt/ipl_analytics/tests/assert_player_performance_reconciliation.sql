with expected as (
    select
        match_id,
        sum(batter_runs) as runs_scored,
        sum(is_ball_faced) as balls_faced,
        sum(bowler_wickets) as wickets,
        sum(bowler_runs_conceded) as runs_conceded,
        coalesce(count_if(is_illegal_delivery = 0), 0) as balls_bowled
    from {{ ref('int_match_deliveries') }}
    where not is_super_over
    group by match_id
),
actual as (
    select
        match_id,
        sum(runs_scored) as runs_scored,
        sum(balls_faced) as balls_faced,
        sum(wickets) as wickets,
        sum(runs_conceded) as runs_conceded,
        sum(balls_bowled) as balls_bowled
    from {{ ref('fact_player_performance') }}
    group by match_id
)
select coalesce(e.match_id, a.match_id) as match_id
from expected e
full outer join actual a on e.match_id = a.match_id
where e.match_id is null or a.match_id is null
   or e.runs_scored is distinct from a.runs_scored
   or e.balls_faced is distinct from a.balls_faced
   or e.wickets is distinct from a.wickets
   or e.runs_conceded is distinct from a.runs_conceded
   or e.balls_bowled is distinct from a.balls_bowled
