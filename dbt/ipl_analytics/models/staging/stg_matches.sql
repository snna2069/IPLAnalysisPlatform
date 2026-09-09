{{ config(materialized='view') }}

with source_matches as (
    select
        record_id,
        source_file,
        file_hash,
        raw_payload,
        loaded_at
    from {{ source('raw', 'raw_matches') }}
),
cleaned as (
    select
        record_id::varchar as match_id,
        nullif(trim(raw_payload:info:season::varchar), '') as season,
        try_to_date(raw_payload:info:dates[0]::varchar) as match_date,
        nullif(trim(raw_payload:info:venue::varchar), '') as venue,
        {{ standardize_team("raw_payload:info:teams[0]::varchar") }} as team_1,
        {{ standardize_team("raw_payload:info:teams[1]::varchar") }} as team_2,
        {{ standardize_team("raw_payload:info:toss:decision::varchar") }} as toss_decision,
        {{ standardize_team("raw_payload:info:toss:won::varchar") }} as toss_winner,
        {{ standardize_team("raw_payload:info:outcome:winner::varchar") }} as winner,
        nullif(trim(raw_payload:info:outcome:result::varchar), '') as result_type,
        try_to_number(raw_payload:info:outcome:margin:runs::varchar) as win_by_runs,
        try_to_number(raw_payload:info:outcome:margin:wickets::varchar) as win_by_wickets,
        source_file,
        file_hash,
        loaded_at
    from source_matches
)
select *
from cleaned
where match_id is not null
