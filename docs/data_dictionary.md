# Analytics Data Dictionary

The tables below are dbt-generated models in `IPL_ANALYTICS.ANALYTICS`. Power BI and Streamlit should consume these tables instead of raw `VARIANT` payloads. All marts use uppercase Snowflake identifiers by default; names are shown in the project SQL style.

## Dimension Tables

### `DIM_PLAYER`

**Grain:** one row per player.

| Column | Type/role | Description |
|---|---|---|
| `PLAYER_KEY` | surrogate key | Stable dbt key generated from player name. |
| `PLAYER_ID` | business key | Source player identifier. |
| `PLAYER_NAME` | attribute | Standardized player display name. |
| `PLAYING_ROLE` | attribute | Source playing role when available. |
| `NATIONALITY` | attribute | Source nationality when available. |
| `SOURCE_FILE` | audit | Raw source file. |
| `LOADED_AT` | audit timestamp | Raw load timestamp. |

### `DIM_TEAM`

**Grain:** one row per standardized team.

| Column | Type/role | Description |
|---|---|---|
| `TEAM_KEY` | surrogate key | Stable key generated from standardized team name. |
| `TEAM_ID` | business key | Source team identifier or deterministic fallback. |
| `TEAM_NAME` | attribute | Standardized team name. |
| `SHORT_NAME` | attribute | Source short name when available. |
| `SOURCE_FILE` | audit | Raw source file. |
| `LOADED_AT` | audit timestamp | Raw load timestamp. |

### `DIM_SEASON`

**Grain:** one row per IPL season.

| Column | Type/role | Description |
|---|---|---|
| `SEASON_KEY` | surrogate key | Stable key generated from season. |
| `SEASON` | business attribute | Season label. |
| `SEASON_NUMBER` | numeric attribute | Numeric season when parseable. |

### `DIM_VENUE`

**Grain:** one row per venue.

| Column | Type/role | Description |
|---|---|---|
| `VENUE_KEY` | surrogate key | Stable key generated from venue. |
| `VENUE` | business attribute | Source venue name. |
| `STANDARDIZED_VENUE` | attribute | Trimmed venue display value. |

### `DIM_MATCH`

**Grain:** one row per match.

| Column | Type/role | Description |
|---|---|---|
| `MATCH_KEY` | surrogate key | Stable key generated from match ID. |
| `MATCH_ID` | business key | Source match identifier. |
| `SEASON_KEY` | foreign key | References `DIM_SEASON`. |
| `VENUE_KEY` | foreign key | References `DIM_VENUE`. |
| `TEAM_1_KEY`, `TEAM_2_KEY` | foreign keys | References `DIM_TEAM` for participating teams. |
| `MATCH_DATE` | date | Parsed match date. |
| `SEASON`, `VENUE`, `TEAM_1`, `TEAM_2` | denormalized attributes | Convenient match context for consumers. |
| `TOSS_WINNER`, `TOSS_DECISION` | outcome attributes | Toss result. |
| `WINNER`, `RESULT_TYPE` | outcome attributes | Match result. |
| `WIN_BY_RUNS`, `WIN_BY_WICKETS` | numeric measures | Winning margin by result type. |

## Fact Tables

### `FACT_MATCHES`

**Grain:** one row per match.

Contains `MATCH_KEY`, `SEASON_KEY`, `VENUE_KEY`, `TEAM_1_KEY`, `TEAM_2_KEY`, `WINNER_KEY`, match date/context, toss attributes, result, and win margins. Use it for match counts, wins, win percentages, toss analysis, venues, and season outcomes.

### `FACT_DELIVERIES`

**Grain:** one row per delivery.

| Column group | Columns | Description |
|---|---|---|
| Keys | `DELIVERY_KEY`, `MATCH_KEY`, `BATTER_KEY`, `BOWLER_KEY`, `BATTING_TEAM_KEY` | Delivery and analytical context keys. |
| Sequence | `DELIVERY_ID`, `INNINGS_NUMBER`, `OVER_NUMBER`, `BALL_NUMBER` | Ball-level ordering. |
| Participants | `BATTING_TEAM`, `BATTER`, `BOWLER`, `NON_STRIKER` | Players and team involved. |
| Runs | `BATTER_RUNS`, `EXTRA_RUNS`, `TOTAL_RUNS` | Runs recorded for the delivery. |
| Extras | `WIDES`, `NO_BALLS`, `BYES`, `LEG_BYES`, `PENALTY_RUNS` | Extra-run categories. |
| Wickets | `PLAYER_OUT`, `DISMISSAL_KIND`, `IS_WICKET` | Dismissal details and flag. |
| Flags | `IS_FOUR`, `IS_SIX`, `IS_ILLEGAL_DELIVERY` | dbt-derived cricket indicators. |

### `FACT_PLAYER_PERFORMANCE`

**Grain:** one row per player per match.

| Column | Type/role | Description |
|---|---|---|
| `PERFORMANCE_KEY` | surrogate key | Match/player performance key. |
| `MATCH_KEY` | foreign key | References `DIM_MATCH`. |
| `PLAYER_KEY` | foreign key | References `DIM_PLAYER`. |
| `MATCH_ID`, `PLAYER_NAME` | context | Convenient display fields. |
| `RUNS_SCORED`, `BALLS_FACED` | batting measures | Batting production and opportunity. |
| `FOURS`, `SIXES` | batting measures | Boundary counts. |
| `WICKETS`, `RUNS_CONCEDED`, `BALLS_BOWLED` | bowling measures | Bowling production and opportunity. |
| `STRIKE_RATE` | rate | Runs per 100 balls. |
| `BOWLING_AVERAGE` | rate | Runs conceded per wicket when wickets exist. |

## Consumer Guidance

- Join dimensions to facts through surrogate keys with single-direction relationships.
- Treat `FACT_DELIVERIES` as the high-volume table; aggregate it before presenting broad visuals.
- Prefer `FACT_PLAYER_PERFORMANCE` for player comparison because it is already aggregated at match/player grain.
- Do not rebuild team standardization, delivery flags, or player performance logic in Power BI or Streamlit.
- `SOURCE_FILE` and `LOADED_AT` are audit fields and should be hidden from default consumer views.