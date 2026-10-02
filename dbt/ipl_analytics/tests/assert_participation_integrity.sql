with team_counts as (
    select match_key, count(*) as teams, sum(is_win) as wins
    from {{ ref('bridge_match_team') }}
    group by match_key
)
select m.match_key
from {{ ref('fact_matches') }} m
left join team_counts t using (match_key)
where coalesce(t.teams, 0) != 2
   or t.wins != iff(m.match_winner is null, 0, 1)
union all
select r.match_key
from {{ ref('bridge_player_match_team') }} r
left join {{ ref('bridge_match_team') }} t
    on r.match_key = t.match_key and r.team_key = t.team_key
where t.match_team_key is null
union all
select p.match_key
from {{ ref('fact_player_performance') }} p
left join {{ ref('bridge_player_match_team') }} r
    on p.match_key = r.match_key and p.player_key = r.player_key
where r.player_match_key is null
