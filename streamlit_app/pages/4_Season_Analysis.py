from __future__ import annotations

import streamlit as st

from streamlit_app.data import app_css, query, safe_options, show_header, sidebar_filters


st.set_page_config(page_title="Season Analysis | IPL Analytics", page_icon="◒", layout="wide")
app_css()
filters = sidebar_filters(safe_options())
show_header("SEASON ANALYSIS", "The story changes every year.", "Follow champions, leading performers, and the rhythm of runs and wickets across IPL history.")

match_conditions = ["1=1"]
match_params: list[str] = []
if filters["season"] != "All":
    match_conditions.append("m.season = %s")
    match_params.append(filters["season"])
if filters["team"] != "All":
    match_conditions.append("(m.team_1 = %s or m.team_2 = %s)")
    match_params.extend([filters["team"], filters["team"]])
if filters["venue"] != "All":
    match_conditions.append("m.venue = %s")
    match_params.append(filters["venue"])
if filters["player"] != "All":
    match_conditions.append("exists (select 1 from IPL_ANALYTICS.ANALYTICS.BRIDGE_PLAYER_MATCH_TEAM r where r.match_key = m.match_key and r.player_name = %s)")
    match_params.append(filters["player"])
match_where = " and ".join(match_conditions)
performance_conditions = list(match_conditions)
performance_params = list(match_params)
if filters["player"] != "All":
    performance_conditions.append("p.player_name = %s")
    performance_params.append(filters["player"])
if filters["team"] != "All":
    performance_conditions.append("exists (select 1 from IPL_ANALYTICS.ANALYTICS.BRIDGE_PLAYER_MATCH_TEAM r where r.match_key = p.match_key and r.player_key = p.player_key and r.team_name = %s)")
    performance_params.append(filters["team"])
performance_where = " and ".join(performance_conditions)

try:
    trends = query(
        f"""
        select m.season, count(distinct m.match_key) as matches,
               sum(d.total_runs) as runs, sum(d.is_wicket) as wickets
        from IPL_ANALYTICS.ANALYTICS.FACT_MATCHES m
        left join IPL_ANALYTICS.ANALYTICS.FACT_DELIVERIES d
          on m.match_key = d.match_key and not d.is_super_over
        where {match_where}
        group by m.season order by try_to_number(m.season)
        """,
        tuple(match_params),
    )
    champions = query(
        f"""
        select c.season, c.champion, c.final_match_id
        from IPL_ANALYTICS.ANALYTICS.FACT_SEASON_RESULTS c
        where c.season in (
            select distinct m.season from IPL_ANALYTICS.ANALYTICS.FACT_MATCHES m
            where {match_where}
        )
        order by c.season desc
        """,
        tuple(match_params),
    )
    performers = query(
        f"""
        select p.player_name,
               sum(p.runs_scored) as runs, sum(p.wickets) as wickets
        from IPL_ANALYTICS.ANALYTICS.FACT_PLAYER_PERFORMANCE p
        join IPL_ANALYTICS.ANALYTICS.DIM_MATCH m using (match_key)
        where {performance_where}
        group by p.player_name
        """,
        tuple(performance_params),
    )
    if trends.empty:
        st.info("No season data matches the selected filter.")
    else:
        kpi = st.columns(3)
        champion = "Select one season"
        if filters["season"] != "All":
            known_champions = champions["CHAMPION"].dropna()
            champion = known_champions.iloc[0] if not known_champions.empty else "Not available"
        top_runs = performers.sort_values("RUNS", ascending=False).iloc[0]["PLAYER_NAME"] if not performers.empty else "Not available"
        top_wickets = performers.sort_values("WICKETS", ascending=False).iloc[0]["PLAYER_NAME"] if not performers.empty else "Not available"
        kpi[0].metric("Champion", champion)
        kpi[1].metric("Top run scorer", top_runs)
        kpi[2].metric("Top wicket taker", top_wickets)
        left, right = st.columns(2)
        with left:
            st.subheader("Runs by season")
            st.line_chart(trends.set_index("SEASON")["RUNS"], color="#e9c46a")
        with right:
            st.subheader("Wickets by season")
            st.line_chart(trends.set_index("SEASON")["WICKETS"], color="#2a9d8f")
        st.subheader("Season comparison")
        st.dataframe(trends, use_container_width=True, hide_index=True)
        st.subheader("Champion record")
        st.dataframe(champions, use_container_width=True, hide_index=True)
        st.caption("Champions come only from a unique fixture explicitly marked as the season final. Missing, ambiguous, or unresolved finals have no champion. Team, venue, and player filters select seasons in view, not a different champion. Runs, wickets, and player totals exclude super overs.")
except Exception as exc:
    st.error(f"Season analysis could not load: {exc}")
