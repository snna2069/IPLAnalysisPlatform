# IPL Analytics Power BI Dashboard Design

## Purpose

This document defines the Phase 6 Power BI semantic model and portfolio dashboard design for the Snowflake analytics schema. Power BI should consume the dbt-generated tables in `IPL_ANALYTICS.ANALYTICS`; it should not repeat JSON parsing, team-name standardization, delivery-level cleansing, or dimensional modeling.

The dashboard is designed for two audiences:

- **Portfolio reviewers:** clear data-engineering lineage, polished visual hierarchy, and visible business questions.
- **Cricket analysts:** fast comparison of teams, players, seasons, venues, tosses, and match outcomes.

## Snowflake Connection

Use the native **Snowflake connector** in Power BI Desktop:

1. Get Data -> Snowflake.
2. Server: the Snowflake account locator/host supplied by the account administrator.
3. Warehouse: `IPL_ANALYTICS_WH`.
4. Database: `IPL_ANALYTICS`.
5. Select the `ANALYTICS` schema.
6. Import only the dbt mart tables listed below.

Recommended authentication is Microsoft Entra ID or Snowflake OAuth for a shared portfolio deployment. Username/password authentication is acceptable for local development but credentials must not be embedded in the PBIX, source files, screenshots, or documentation.

Create a least-privilege reporting role with `USAGE` on the database/schema and `SELECT` on analytics tables. Do not grant Power BI access to `RAW`, `STAGING`, or `INTERMEDIATE` unless troubleshooting is explicitly required.

### Storage mode

Use **Import** mode for a portfolio presentation and small-to-medium IPL history. It produces responsive visuals and predictable Snowflake credit usage after scheduled refreshes. Use **DirectQuery** only when near-real-time data or a very large delivery history requires it; configure an explicit refresh/query budget and avoid high-cardinality delivery visuals on the landing page.

## Recommended Semantic Model

Use a star schema with one shared match context and two primary analytic facts:

```text
                         dim_season
                             |
 dim_team ---- dim_match ---- dim_venue
                  |   |   |
                  |   |   +---- fact_matches
                  |   |
                  |   +-------- fact_deliveries ---- dim_player (batter/bowler roles)
                  |
                  +------------ fact_player_performance ---- dim_player
```

### Tables and grain

| Table | Grain | Purpose |
|---|---|---|
| `dim_player` | One row per player | Player identity, role, nationality, and player key |
| `dim_team` | One row per standardized team | Team identity and display names |
| `dim_season` | One row per season | Season slicer and chronological comparison |
| `dim_venue` | One row per venue | Venue grouping and match-location analysis |
| `dim_match` | One row per match | Conformed match, season, venue, team, toss, winner, and margin context |
| `fact_matches` | One row per match | Match-level outcomes, winners, toss, and margins |
| `fact_deliveries` | One row per delivery | Runs, extras, wickets, batter, bowler, innings, and over analysis |
| `fact_player_performance` | One row per player per match | Runs, balls, fours, sixes, wickets, conceded runs, balls bowled, strike rate, and bowling average |

### Relationships

Create these single-direction, one-to-many relationships with the dimension on the `1` side:

| From dimension | To fact | Key | Cardinality |
|---|---|---|---|
| `dim_match[match_key]` | `fact_matches[match_key]` | `match_key` | 1:* |
| `dim_match[match_key]` | `fact_deliveries[match_key]` | `match_key` | 1:* |
| `dim_match[match_key]` | `fact_player_performance[match_key]` | `match_key` | 1:* |
| `dim_season[season_key]` | `dim_match[season_key]` | `season_key` | 1:* |
| `dim_venue[venue_key]` | `dim_match[venue_key]` | `venue_key` | 1:* |
| `dim_team[team_key]` | `fact_matches[team_1_key]` | `team_1_key` | 1:* |
| `dim_team[team_key]` | `fact_matches[team_2_key]` | `team_2_key` | 1:* |
| `dim_team[team_key]` | `fact_deliveries[batting_team_key]` | `batting_team_key` | 1:* |
| `dim_player[player_key]` | `fact_player_performance[player_key]` | `player_key` | 1:* |

### Role-playing dimensions

Power BI cannot use one active relationship from `dim_team` to both `team_1_key` and `team_2_key` without ambiguity. Use one of these patterns:

- **Recommended for this portfolio:** keep `dim_team -> fact_matches[team_1_key]` active and `dim_team -> fact_matches[team_2_key]` inactive. Use `USERELATIONSHIP` in comparison measures, or create two thin role-playing dimensions named `dim_team_home` and `dim_team_away` in the semantic model.
- Keep the delivery team relationship active for batting-team analysis.
- Do not create bidirectional relationships. They can produce ambiguous filter paths between match, team, and fact tables.

For batter and bowler analysis, the current dbt mart exposes deterministic name-based keys in `fact_deliveries` but does not expose separate `batter_key` and `bowler_key` relationships in the model design. Use `fact_player_performance` for player comparison pages. If ball-level player slicers are required later, add role-playing `dim_player_batter` and `dim_player_bowler` relationships in dbt rather than rebuilding them in Power BI.

## Required DAX Measures

Create a dedicated, hidden table named `_Measures` and place all measures there. Format counts as whole numbers, rates as percentages or one decimal place, and margins as whole numbers.

### Executive KPIs

```DAX
Total Matches =
DISTINCTCOUNT ( fact_matches[match_key] )

Total Seasons =
DISTINCTCOUNT ( dim_season[season_key] )

Total Players =
DISTINCTCOUNT ( dim_player[player_key] )

Total Teams =
DISTINCTCOUNT ( dim_team[team_key] )

Total Runs =
SUM ( fact_deliveries[total_runs] )

Total Wickets =
SUM ( fact_deliveries[is_wicket] )

Highest Run Scorer =
VAR PlayerTotals =
    ADDCOLUMNS (
        ALLSELECTED ( dim_player[player_key], dim_player[player_name] ),
        "Runs", CALCULATE ( SUM ( fact_player_performance[runs_scored] ) )
    )
RETURN
    CONCATENATEX ( TOPN ( 1, PlayerTotals, [Runs], DESC ), dim_player[player_name], ", " )

Highest Wicket Taker =
VAR PlayerTotals =
    ADDCOLUMNS (
        ALLSELECTED ( dim_player[player_key], dim_player[player_name] ),
        "Wickets", CALCULATE ( SUM ( fact_player_performance[wickets] ) )
    )
RETURN
    CONCATENATEX ( TOPN ( 1, PlayerTotals, [Wickets], DESC ), dim_player[player_name], ", " )
```

### Team analysis

`fact_matches` contains team keys in two roles. For a simple team wins visual, use a disconnected team selector or a role-playing team dimension. With `dim_team_home` as the active team role:

```DAX
Team Wins =
CALCULATE (
    [Total Matches],
    FILTER (
        fact_matches,
        fact_matches[winner_key]
            = SELECTEDVALUE ( dim_team[team_key] )
    )
)

Team Matches =
[Total Matches]

Team Win Percentage =
DIVIDE ( [Team Wins], [Team Matches], 0 )

Runs Per Match =
DIVIDE ( [Total Runs], [Total Matches], 0 )
```

For a robust team win chart, add a dbt-owned bridge model in a future revision with one row per match/team participation. That avoids duplicating team-role logic in DAX and makes win percentage, head-to-head, and season performance naturally filterable.

```DAX
Head To Head Wins =
CALCULATE (
    [Total Matches],
    fact_matches[winner_key] = SELECTEDVALUE ( dim_team[team_key] )
)
```

### Player analysis

```DAX
Runs Scored =
SUM ( fact_player_performance[runs_scored] )

Wickets Taken =
SUM ( fact_player_performance[wickets] )

Balls Faced =
SUM ( fact_player_performance[balls_faced] )

Strike Rate =
DIVIDE ( [Runs Scored] * 100, [Balls Faced], 0 )

Runs Conceded =
SUM ( fact_player_performance[runs_conceded] )

Balls Bowled =
SUM ( fact_player_performance[balls_bowled] )

Economy Rate =
DIVIDE ( [Runs Conceded] * 6, [Balls Bowled], 0 )

Fours =
SUM ( fact_player_performance[fours] )

Sixes =
SUM ( fact_player_performance[sixes] )
```

### Match and season analysis

```DAX
Average Win By Runs =
AVERAGE ( fact_matches[win_by_runs] )

Average Win By Wickets =
AVERAGE ( fact_matches[win_by_wickets] )

Toss Wins By Winner =
CALCULATE (
    [Total Matches],
    FILTER ( fact_matches, fact_matches[toss_winner] = fact_matches[winner] )
)

Toss Advantage Percentage =
DIVIDE ( [Toss Wins By Winner], [Total Matches], 0 )

Average Runs Per Delivery =
DIVIDE ( [Total Runs], COUNTROWS ( fact_deliveries ), 0 )

High Scoring Matches =
COUNTROWS (
    FILTER (
        VALUES ( dim_match[match_key] ),
        CALCULATE ( [Total Runs] ) >= 350
    )
)
```

The 350-run threshold should be documented in the report tooltip and can be replaced with a what-if parameter if the audience needs to adjust it.

## Dashboard Pages

### 1. Executive Overview

**Purpose:** communicate the scale and most important outcomes within five seconds.

- KPI cards: Total Matches, Total Seasons, Total Players, Total Teams.
- Two callout cards: Highest Run Scorer and Highest Wicket Taker.
- Line chart: matches by season.
- Clustered bar: top five teams by wins.
- Small “data coverage” subtitle: latest season, earliest season, and refresh timestamp.
- Slicers: season, team, venue.

### 2. Team Analysis

- Ranked horizontal bar: wins by team.
- Dot plot or bar: win percentage by team, with minimum-match tooltip.
- Line chart: team wins by season.
- Matrix: head-to-head teams with wins and win percentage.
- Tooltip fields: matches played, wins, losses, runs per match, and latest season.
- Slicers: season range, team, venue.

### 3. Player Analysis

- Toggle or separate views for top run scorers and top wicket takers.
- Scatter plot: runs scored vs strike rate; bubble size = balls faced.
- Scatter plot: wickets vs economy rate; bubble size = balls bowled.
- Player comparison table: runs, wickets, strike rate, economy rate, fours, sixes.
- Slicers: player, season, team, minimum balls faced/bowled.

### 4. Match Analysis

- Filled or bar map alternative: matches by venue. Use a bar chart if geographic coordinates are unavailable.
- 100% stacked bar: toss decision by season.
- Histogram: win-by-runs and win-by-wickets margins.
- Ranked bar: highest-scoring matches with match date, teams, venue, and total runs.
- Detail table with drill-through to match and delivery context.
- Slicers: season, venue, winner, toss decision, result type.

### 5. Season Analysis

- Champion-by-season table or ribbon chart.
- Combo chart: total runs and wickets by season.
- Top performers table with selected season context.
- Small multiples: team win totals by season.
- Season comparison cards: matches, average runs per match, highest score, leading batter, leading bowler.
- Slicers: season, team, venue.

## Wireframe

```text
+--------------------------------------------------------------------------------+
| IPL ANALYTICS                         Season [All] Team [All] Venue [All]      |
+--------------------------------------------------------------------------------+
| Matches | Seasons | Players | Teams | Highest Run Scorer | Highest Wicket Taker|
+--------------------------------------------------------------------------------+
| Runs / Wickets by Season                    | Top Teams by Wins              |
|                                             |                                |
|                                             |                                |
+---------------------------------------------+--------------------------------+
| Featured Insight / selected-page narrative  | Refresh: YYYY-MM-DD           |
+--------------------------------------------------------------------------------+
| Executive | Teams | Players | Matches | Seasons       [page navigation]          |
+--------------------------------------------------------------------------------+
```

Use the same restrained header, slicer strip, card spacing, and footer navigation on every page. Keep charts aligned to a 12-column grid, reserve the top row for the page question and filters, and place detail tables below the primary comparison visual.

## Portfolio Presentation Recommendations

- Use a dark charcoal canvas with one IPL-inspired accent color and high-contrast white text; use team colors sparingly for categorical emphasis.
- Keep the Executive Overview intentionally sparse. It should show data lineage and decision-ready KPIs, not every available metric.
- Add a compact “Model: dbt -> Snowflake -> Power BI” lineage badge or tooltip, not a large explanatory block.
- Include page-level tooltips describing grain: match, delivery, or player-match.
- Add drill-through from team, player, and match visuals to detail pages only if the report remains responsive.
- Display “Data last refreshed” from the Snowflake/dbt refresh metadata when that field is exposed to the semantic model.
- Use accessible color contrast, alt text, meaningful visual titles, and avoid encoding meaning by color alone.
- Hide technical keys, source file names, and hash columns from report view; retain them only for audit/debug pages.

## Modeling Boundaries

The following remain in dbt, not Power BI:

- JSON extraction from Snowflake `VARIANT` payloads.
- Team-name standardization.
- Match, delivery, and player-performance grain.
- Surrogate-key generation.
- Deduplication and null handling.
- Delivery-derived flags such as boundaries, wickets, and legal deliveries.
- New bridge tables needed for clean team participation analysis.

Power BI owns only semantic relationships, formatting, interactive filters, aggregations, rankings, and presentation measures. Any repeated or complex business calculation should be promoted back into dbt so it is tested and reusable outside the dashboard.
