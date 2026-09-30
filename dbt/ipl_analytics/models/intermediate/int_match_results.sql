{{ config(materialized='table') }}

select
    match_id,
    season,
    match_date,
    venue,
    team_1,
    team_2,
    toss_winner,
    toss_decision,
    winner,
    eliminator,
    result_method,
    -- Cricsheet omits outcome.result for a normal win and sets it only for
    -- 'tie', 'no result', or 'draw'.
    coalesce(result_type, iff(winner is not null, 'win', 'unknown')) as result_type,
    -- Nulls mean "margin not applicable" (tie, no result, or the other margin
    -- type); they must not be collapsed into a real margin of zero.
    win_by_runs,
    win_by_wickets,
    -- A tie decided by a super over records no outcome.winner, only an eliminator.
    coalesce(winner, eliminator) as match_winner,
    case
        when winner = team_1 then team_1
        when winner = team_2 then team_2
    end as winner_side,
    source_file,
    file_hash,
    loaded_at
from {{ ref('stg_matches') }}
