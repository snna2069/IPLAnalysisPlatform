from __future__ import annotations

import streamlit as st

from streamlit_app.data import app_css, query, safe_options, show_header, sidebar_filters


st.set_page_config(page_title="Player Analysis | IPL Analytics", page_icon="◉", layout="wide")
app_css()
filters = sidebar_filters(safe_options())
show_header("PLAYER ANALYSIS", "The people behind the numbers.", "Find the batters who changed games, the bowlers who closed them, and the all-round profiles between.")

conditions = ["1=1"]
params = []
if filters["season"] != "All":
    conditions.append("m.season = %s")
    params.append(filters["season"])
if filters["player"] != "All":
    conditions.append("p.player_name = %s")
    params.append(filters["player"])
if filters["team"] != "All":
    conditions.append("exists (select 1 from IPL_ANALYTICS.ANALYTICS.BRIDGE_PLAYER_MATCH_TEAM r where r.match_key = p.match_key and r.player_key = p.player_key and r.team_name = %s)")
    params.append(filters["team"])
if filters["venue"] != "All":
    conditions.append("m.venue = %s")
    params.append(filters["venue"])
where = " AND ".join(conditions)

try:
    performance = query(
        f"""
         select player_name, runs, wickets, balls_faced, runs_conceded, balls_bowled,
             round(100 * runs / nullif(balls_faced, 0), 2) as strike_rate,
             round(6 * runs_conceded / nullif(balls_bowled, 0), 2) as economy_rate
         from (
             select p.player_name, sum(p.runs_scored) as runs, sum(p.wickets) as wickets,
                 sum(p.balls_faced) as balls_faced, sum(p.runs_conceded) as runs_conceded,
                 sum(p.balls_bowled) as balls_bowled
             from IPL_ANALYTICS.ANALYTICS.FACT_PLAYER_PERFORMANCE p
             join IPL_ANALYTICS.ANALYTICS.DIM_MATCH m using (match_key)
             where {where}
             group by p.player_name
         ) stats
        order by runs desc
        """,
        tuple(params),
    )
    if performance.empty:
        st.info("No player performance matches the selected filters.")
    else:
        top = performance.iloc[0]
        kpi = st.columns(4)
        kpi[0].metric("Top run scorer", top["PLAYER_NAME"])
        kpi[1].metric("Runs", f"{int(top['RUNS']):,}")
        kpi[2].metric("Top wickets", performance.sort_values("WICKETS", ascending=False).iloc[0]["PLAYER_NAME"])
        kpi[3].metric("Players in view", f"{len(performance):,}")
        left, right = st.columns(2)
        with left:
            st.subheader("Runs leaderboard")
            st.bar_chart(performance.head(10).set_index("PLAYER_NAME")["RUNS"], color="#e9c46a")
        with right:
            st.subheader("Wickets leaderboard")
            st.bar_chart(performance.sort_values("WICKETS", ascending=False).head(10).set_index("PLAYER_NAME")["WICKETS"], color="#2a9d8f")
        st.subheader("Player comparison")
        st.dataframe(performance, use_container_width=True, hide_index=True)
        st.caption("Regular innings only; super overs are excluded. Balls faced exclude wides but include no-balls. Bowler wickets exclude run-outs and other non-bowler dismissals; conceded runs exclude byes, leg-byes, and penalties. The team filter selects players representing that team.")
except Exception as exc:
    st.error(f"Player analysis could not load: {exc}")
