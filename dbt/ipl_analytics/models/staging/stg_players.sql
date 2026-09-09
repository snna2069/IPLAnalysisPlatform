{{ config(materialized='view') }}

select distinct
    coalesce(nullif(trim(raw_payload:id::varchar), ''), record_id::varchar) as player_id,
    nullif(trim(coalesce(raw_payload:name::varchar, raw_payload:player_name::varchar)), '') as player_name,
    nullif(trim(raw_payload:role::varchar), '') as playing_role,
    nullif(trim(raw_payload:nationality::varchar), '') as nationality,
    source_file,
    file_hash,
    loaded_at
from {{ source('raw', 'raw_players') }}
where coalesce(nullif(trim(raw_payload:id::varchar), ''), record_id::varchar) is not null
