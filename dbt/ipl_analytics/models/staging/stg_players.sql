{{ config(materialized='view') }}

with source_players as (
    select
        coalesce(nullif(trim(raw_payload:id::varchar), ''), record_id::varchar) as player_id,
        nullif(trim(coalesce(raw_payload:name::varchar, raw_payload:player_name::varchar)), '') as player_name,
        nullif(trim(raw_payload:role::varchar), '') as playing_role,
        nullif(trim(raw_payload:nationality::varchar), '') as nationality,
        source_file,
        file_hash,
        loaded_at,
        1 as source_priority
    from {{ source('raw', 'raw_players') }}
), match_players as (
    -- Cricsheet's default ZIP stores player names in match metadata, not RAW_PLAYERS.
    select
        md5(player.value::varchar) as player_id,
        nullif(trim(player.value::varchar), '') as player_name,
        null as playing_role,
        null as nationality,
        matches.source_file,
        matches.file_hash,
        matches.loaded_at,
        2 as source_priority
    from {{ source('raw', 'raw_matches') }} matches,
        lateral flatten(input => matches.raw_payload:info:players) team_players,
        lateral flatten(input => team_players.value) player
), combined as (
    select * from source_players
    union all
    select * from match_players
)
select player_id, player_name, playing_role, nationality, source_file, file_hash, loaded_at
from combined
where player_id is not null
  and player_name is not null
qualify row_number() over (partition by player_name order by source_priority, loaded_at desc) = 1
