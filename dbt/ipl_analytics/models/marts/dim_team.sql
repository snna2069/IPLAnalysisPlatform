{{ config(materialized='table') }}

with source_teams as (
    select team_id, team_name, short_name, source_file, loaded_at
    from {{ ref('stg_teams') }}
), match_teams as (
    select distinct team_1 as team_name from {{ ref('stg_matches') }} where team_1 is not null
    union
    select distinct team_2 from {{ ref('stg_matches') }} where team_2 is not null
), combined as (
    select * from source_teams
    union all
    select
        {{ dbt_utils.generate_surrogate_key(['team_name']) }},
        team_name,
        null,
        null,
        null
    from match_teams
)
select distinct
    {{ dbt_utils.generate_surrogate_key(['team_name']) }} as team_key,
    coalesce(team_id, {{ dbt_utils.generate_surrogate_key(['team_name']) }}) as team_id,
    team_name,
    short_name,
    source_file,
    loaded_at
from combined
where team_name is not null
