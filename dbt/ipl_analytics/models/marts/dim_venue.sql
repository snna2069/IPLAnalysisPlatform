{{ config(materialized='table') }}

select distinct
    {{ dbt_utils.generate_surrogate_key(['venue']) }} as venue_key,
    venue,
    nullif(trim(venue), '') as standardized_venue
from {{ ref('stg_matches') }}
where venue is not null
