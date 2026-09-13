-- A match must have two distinct participating teams.
select match_id, team_1, team_2
from {{ ref('stg_matches') }}
where team_1 is null
   or team_2 is null
   or team_1 = team_2
