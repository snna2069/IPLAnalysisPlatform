{{ config(materialized='table') }}

select distinct
    {{ dbt_utils.generate_surrogate_key(['season']) }} as season_key,
    season,
    try_to_number(season) as season_number
from {{ ref('stg_matches') }}
where season is not null
