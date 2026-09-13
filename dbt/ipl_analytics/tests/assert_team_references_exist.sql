-- Both participating teams and the winner must resolve to dim_team.
select match_id, team_name
from (
    select match_id, team_1 as team_name from {{ ref('stg_matches') }}
    union all
    select match_id, team_2 from {{ ref('stg_matches') }}
    union all
    select match_id, winner from {{ ref('stg_matches') }} where winner is not null
) references
left join {{ ref('dim_team') }} teams using (team_name)
where team_name is not null
  and teams.team_key is null
