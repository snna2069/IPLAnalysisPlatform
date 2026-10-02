{{ config(materialized='table') }}

with roster as (
    select
        m.match_id,
        {{ standardize_team('t.key::varchar') }} as team_name,
        nullif(trim(p.value::varchar), '') as player_name
    from {{ ref('stg_matches') }} m,
        lateral flatten(input => m.player_roster) t,
        lateral flatten(input => t.value) p
)
select distinct
    {{ dbt_utils.generate_surrogate_key(['match_id', 'player_name']) }} as player_match_key,
    {{ dbt_utils.generate_surrogate_key(['match_id']) }} as match_key,
    {{ dbt_utils.generate_surrogate_key(['player_name']) }} as player_key,
    {{ dbt_utils.generate_surrogate_key(['team_name']) }} as team_key,
    match_id,
    player_name,
    team_name
from roster
where player_name is not null
