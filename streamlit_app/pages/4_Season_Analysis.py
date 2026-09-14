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
    match_conditions.append("exists (select 1 from IPL_ANALYTICS.ANALYTICS.FACT_PLAYER_PERFORMANCE fp where fp.match_key = m.match_key and fp.player_name = %s)")
    match_params.append(filters["player"])
match_where = " and ".join(match_conditions)

try:
    trends = query(
        f"""
        select m.season, count(distinct m.match_key) as matches,
               sum(d.total_runs) as runs, sum(d.is_wicket) as wickets
        from IPL_ANALYTICS.ANALYTICS.FACT_MATCHES m
        left join IPL_ANALYTICS.ANALYTICS.FACT_DELIVERIES d using (match_key)
        where {match_where}
        group by m.season order by try_to_number(m.season)
        """,
        tuple(match_params),
    )
    champions = query(
        f"""
        select season, winner as champion, count(*) as title_evidence
        from IPL_ANALYTICS.ANALYTICS.FACT_MATCHES m
        where winner is not null
          and {match_where}
        group by season, winner
        qualify row_number() over (partition by season order by title_evidence desc) = 1
        order by try_to_number(season) desc
        """,
        tuple(match_params),
    )
    performers = query(
        f"""
        select m.season, p.player_name,
               sum(p.runs_scored) as runs, sum(p.wickets) as wickets
        from IPL_ANALYTICS.ANALYTICS.FACT_PLAYER_PERFORMANCE p
        join IPL_ANALYTICS.ANALYTICS.DIM_MATCH m using (match_key)
        where {match_where}
        group by m.season, p.player_name
        """,
        tuple(match_params),
    )
    if trends.empty:
        st.info("No season data matches the selected filter.")
    else:
        latest = trends.iloc[-1]
        kpi = st.columns(3)
        champion = champions.iloc[0]["CHAMPION"] if not champions.empty else "Not available"
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
        st.caption("Champion is inferred from the winner recorded in match facts. Confirm the official final result when extending the mart with tournament metadata.")
except Exception as exc:
    st.error(f"Season analysis could not load: {exc}")
