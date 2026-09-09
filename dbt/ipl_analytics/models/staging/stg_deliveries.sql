{{ config(materialized='view') }}

-- Cricsheet match files store innings and deliveries inside RAW_MATCHES.
with flattened as (
    select
        r.record_id as match_id,
        r.source_file,
        r.file_hash,
        r.loaded_at,
        innings.index as innings_number,
        innings.value:team::varchar as batting_team,
        overs.value:over::integer as over_number,
        deliveries.index as ball_number,
        deliveries.value as ball
    from {{ source('raw', 'raw_matches') }} r,
        lateral flatten(input => r.raw_payload:innings) innings,
        lateral flatten(input => innings.value:overs) overs,
        lateral flatten(input => overs.value:deliveries) deliveries
),
cleaned as (
    select
        concat_ws('-', match_id, innings_number, over_number, ball_number) as delivery_id,
        match_id,
        innings_number,
        over_number,
        ball_number,
        {{ standardize_team('batting_team') }} as batting_team,
        nullif(trim(ball:batter::varchar), '') as batter,
        nullif(trim(ball:bowler::varchar), '') as bowler,
        nullif(trim(ball:non_striker::varchar), '') as non_striker,
        coalesce(try_to_number(ball:runs:batter::varchar), 0) as batter_runs,
        coalesce(try_to_number(ball:runs:extras::varchar), 0) as extra_runs,
        coalesce(try_to_number(ball:runs:total::varchar), 0) as total_runs,
        coalesce(try_to_number(ball:extras:wides::varchar), 0) as wides,
        coalesce(try_to_number(ball:extras:noballs::varchar), 0) as no_balls,
        coalesce(try_to_number(ball:extras:byes::varchar), 0) as byes,
        coalesce(try_to_number(ball:extras:legbyes::varchar), 0) as leg_byes,
        coalesce(try_to_number(ball:extras:penalty::varchar), 0) as penalty_runs,
        nullif(trim(ball:wickets[0]:player_out::varchar), '') as player_out,
        nullif(trim(ball:wickets[0]:kind::varchar), '') as dismissal_kind,
        source_file,
        file_hash,
        loaded_at
    from flattened
)
select *
from cleaned
where batter is not null
  and bowler is not null
