{{ config(materialized='table') }}

with final_candidates as (
    select
        season,
        count(*) as final_count,
        max(match_id) as final_match_id,
        max(match_winner) as champion
    from {{ ref('int_match_results') }}
    where event_stage = 'final'
    group by season
)
select
    s.season_key,
    s.season,
    case when f.final_count = 1 and f.champion is not null then f.champion end as champion,
    case when f.final_count = 1 and f.champion is not null then f.final_match_id end as final_match_id
from {{ ref('dim_season') }} s
left join final_candidates f on s.season = f.season
