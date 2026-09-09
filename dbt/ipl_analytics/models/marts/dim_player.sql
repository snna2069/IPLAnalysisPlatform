{{ config(materialized='table') }}

select
    {{ dbt_utils.generate_surrogate_key(['player_id']) }} as player_key,
    player_id,
    player_name,
    playing_role,
    nationality,
    source_file,
    loaded_at
from {{ ref('stg_players') }}
