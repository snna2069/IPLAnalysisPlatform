{{ config(materialized='view') }}

-- Cricsheet publishes one cumulative archive, so a re-download reloads every match
-- under a new FILE_HASH. Keep only the newest copy of each source record, preferring
-- the highest meta.revision because Cricsheet increments it when a match is corrected.
with source_matches as (
    select
        record_id,
        source_file,
        file_hash,
        raw_payload,
        loaded_at
    from {{ source('raw', 'raw_matches') }}
    qualify row_number() over (
        partition by record_id
        order by
            try_to_number(raw_payload:meta:revision::varchar) desc nulls last,
            loaded_at desc,
            file_hash
    ) = 1
),
cleaned as (
    select
        record_id::varchar as match_id,
        try_to_number(raw_payload:meta:revision::varchar) as source_revision,
        nullif(trim(raw_payload:info:season::varchar), '') as season,
        try_to_date(raw_payload:info:dates[0]::varchar) as match_date,
        nullif(trim(raw_payload:info:venue::varchar), '') as venue,
        {{ standardize_team("raw_payload:info:teams[0]::varchar") }} as team_1,
        {{ standardize_team("raw_payload:info:teams[1]::varchar") }} as team_2,
        -- toss.decision is a 'bat'/'field' enum, not a team name.
        lower(nullif(trim(raw_payload:info:toss:decision::varchar), '')) as toss_decision,
        {{ standardize_team("raw_payload:info:toss:winner::varchar") }} as toss_winner,
        {{ standardize_team("raw_payload:info:outcome:winner::varchar") }} as winner,
        -- Set only when a tie is decided by a super over.
        {{ standardize_team("raw_payload:info:outcome:eliminator::varchar") }} as eliminator,
        nullif(trim(raw_payload:info:outcome:result::varchar), '') as result_type,
        nullif(trim(raw_payload:info:outcome:method::varchar), '') as result_method,
        try_to_number(raw_payload:info:outcome:by:runs::varchar) as win_by_runs,
        try_to_number(raw_payload:info:outcome:by:wickets::varchar) as win_by_wickets,
        source_file,
        file_hash,
        loaded_at
    from source_matches
)
select *
from cleaned
where match_id is not null
