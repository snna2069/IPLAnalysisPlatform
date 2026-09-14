from __future__ import annotations

import streamlit as st

from streamlit_app.data import app_css, query, safe_options, show_header, sidebar_filters


st.set_page_config(page_title="Match Analysis | IPL Analytics", page_icon="◌", layout="wide")
app_css()
filters = sidebar_filters(safe_options())
show_header("MATCH ANALYSIS", "Every match leaves a pattern.", "Read outcomes through venues, tosses, margins, and the games where the scoreboard caught fire.")

conditions = ["1=1"]
params = []
if filters["season"] != "All":
    conditions.append("SEASON = %s")
    params.append(filters["season"])
if filters["venue"] != "All":
    conditions.append("VENUE = %s")
    params.append(filters["venue"])
if filters["team"] != "All":
    conditions.append("(TEAM_1 = %s or TEAM_2 = %s)")
    params.extend([filters["team"], filters["team"]])
if filters["player"] != "All":
    conditions.append("MATCH_KEY in (select MATCH_KEY from IPL_ANALYTICS.ANALYTICS.FACT_PLAYER_PERFORMANCE where PLAYER_NAME = %s)")
    params.append(filters["player"])
where = " AND ".join(conditions)

try:
    matches = query(
        f"""
        select match_date, season, venue, team_1, team_2, winner,
               toss_winner, toss_decision, win_by_runs, win_by_wickets,
               match_key
        from IPL_ANALYTICS.ANALYTICS.FACT_MATCHES
        where {where}
        order by match_date desc
        """,
        tuple(params),
    )
    if matches.empty:
        st.info("No matches match the selected filters.")
    else:
        kpi = st.columns(3)
        kpi[0].metric("Matches in view", f"{len(matches):,}")
        kpi[1].metric("Venues", f"{matches['VENUE'].nunique():,}")
        kpi[2].metric("Highest run margin", f"{int(matches['WIN_BY_RUNS'].fillna(0).max()):,}")
        left, right = st.columns(2)
        with left:
            st.subheader("Matches by venue")
            venues = matches["VENUE"].value_counts().head(12)
            st.bar_chart(venues, color="#e76f51")
        with right:
            st.subheader("Toss decisions")
            toss = matches["TOSS_DECISION"].value_counts()
            st.bar_chart(toss, color="#2a9d8f")
        st.subheader("High-scoring matches")
        match_keys = ", ".join(["%s"] * len(matches["MATCH_KEY"].tolist()))
        scoring = query(
            f"""
            select d.match_id, m.match_date, m.team_1, m.team_2, m.venue,
                   sum(d.total_runs) as total_runs
            from IPL_ANALYTICS.ANALYTICS.FACT_DELIVERIES d
            join IPL_ANALYTICS.ANALYTICS.FACT_MATCHES m using (match_key)
            where m.match_key in ({match_keys})
            group by d.match_id, m.match_date, m.team_1, m.team_2, m.venue
            order by total_runs desc limit 10
            """,
            tuple(matches["MATCH_KEY"].tolist()),
        )
        st.dataframe(scoring, use_container_width=True, hide_index=True)
        st.subheader("Match results")
        st.dataframe(matches, use_container_width=True, hide_index=True)
except Exception as exc:
    st.error(f"Match analysis could not load: {exc}")
