{{ config(severity='warn') }}

-- Cricsheet republishes corrected match files with an incremented meta.revision.
-- Staging keeps only the newest copy, so a correction silently supersedes the
-- version analytics were previously built on.
--
-- This warns (rather than fails) because a revision is legitimate source
-- behaviour, not a defect. It compares payload content rather than FILE_HASH,
-- because FILE_HASH covers the whole cumulative archive and therefore changes on
-- every re-download even when no match was corrected.
select
    record_id as match_id,
    count(distinct md5(raw_payload::string)) as distinct_payload_versions,
    min(try_to_number(raw_payload:meta:revision::varchar)) as earliest_revision,
    max(try_to_number(raw_payload:meta:revision::varchar)) as latest_revision,
    min(loaded_at) as first_loaded_at,
    max(loaded_at) as latest_loaded_at
from {{ source('raw', 'raw_matches') }}
group by record_id
having count(distinct md5(raw_payload::string)) > 1
