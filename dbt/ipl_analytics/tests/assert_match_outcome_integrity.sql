-- Cricsheet outcome semantics must stay internally consistent.
--
-- This test is deliberately falsifiable: it fails if the toss or margin field
-- paths regress to names Cricsheet does not publish (F-01, F-02), because the
-- affected columns then arrive empty rather than merely wrong.
select
    match_id,
    team_1,
    team_2,
    toss_winner,
    winner,
    eliminator,
    result_type,
    win_by_runs,
    win_by_wickets
from {{ ref('int_match_results') }}
where
    -- A decided match must name a winner and exactly one victory margin.
    (result_type = 'win' and winner is null)
    or (result_type = 'win' and win_by_runs is null and win_by_wickets is null)
    or (win_by_runs is not null and win_by_wickets is not null)
    -- A tie is resolved by an eliminator, never by outcome.winner.
    or (result_type = 'tie' and winner is not null)
    -- Participants must be one of the two teams that played.
    or (winner is not null and winner not in (team_1, team_2))
    or (eliminator is not null and eliminator not in (team_1, team_2))
    or (toss_winner is not null and toss_winner not in (team_1, team_2))
