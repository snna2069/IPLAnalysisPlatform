-- Performance metrics cannot be negative and strike rate cannot be negative.
select match_id, player_name, runs_scored, wickets, strike_rate
from {{ ref('fact_player_performance') }}
where runs_scored < 0
   or wickets < 0
   or strike_rate < 0
