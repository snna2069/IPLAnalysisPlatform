-- Every match must resolve to one season dimension member.
select match_id, season
from {{ ref('stg_matches') }} matches
left join {{ ref('dim_season') }} seasons using (season)
where seasons.season_key is null
