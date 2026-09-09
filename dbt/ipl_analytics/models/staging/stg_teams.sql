{{ config(materialized='view') }}

select distinct
    coalesce(nullif(trim(raw_payload:id::varchar), ''), record_id::varchar) as team_id,
    {{ standardize_team("coalesce(raw_payload:name::varchar, raw_payload:team_name::varchar, record_id::varchar)") }} as team_name,
    nullif(trim(raw_payload:short_name::varchar), '') as short_name,
    source_file,
    file_hash,
    loaded_at
from {{ source('raw', 'raw_teams') }}
where coalesce(nullif(trim(raw_payload:id::varchar), ''), record_id::varchar) is not null
