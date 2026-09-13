from __future__ import annotations

import streamlit as st

from streamlit_app.data import app_css, query, safe_options, show_header, sidebar_filters


st.set_page_config(page_title="IPL Analytics", page_icon="🏏", layout="wide", initial_sidebar_state="expanded")
app_css()
options = safe_options()
filters = sidebar_filters(options)
show_header(
    "IPL DATA PLATFORM / PHASE 7",
    "The league, in focus.",
    "A Snowflake-powered exploration of IPL matches, teams, players, venues, and seasons. Built on dbt analytics marts for fast, trustworthy analysis.",
)

try:
    matches = query("SELECT COUNT(DISTINCT MATCH_KEY) AS VALUE FROM IPL_ANALYTICS.ANALYTICS.FACT_MATCHES")
    seasons = query("SELECT COUNT(DISTINCT SEASON_KEY) AS VALUE FROM IPL_ANALYTICS.ANALYTICS.DIM_SEASON")
    players = query("SELECT COUNT(DISTINCT PLAYER_KEY) AS VALUE FROM IPL_ANALYTICS.ANALYTICS.DIM_PLAYER")
    teams = query("SELECT COUNT(DISTINCT TEAM_KEY) AS VALUE FROM IPL_ANALYTICS.ANALYTICS.DIM_TEAM")
    cols = st.columns(4)
    for column, label, frame in zip(cols, ["Matches", "Seasons", "Players", "Teams"], [matches, seasons, players, teams]):
        column.metric(label, f"{int(frame.iloc[0, 0]):,}")

    left, right = st.columns([1.4, 1])
    with left:
        st.markdown('<div class="section-kicker">Why this exists</div>', unsafe_allow_html=True)
        st.subheader("One view across every cricket question")
        st.write("Trace performance from season trends to a single delivery. The frontend reads only curated Snowflake analytics tables; ingestion, standardization, and cricket calculations remain tested in the upstream Python and dbt layers.")
        st.info("Use the pages in the sidebar to compare teams, profile players, inspect match patterns, and follow season stories.")
    with right:
        st.markdown('<div class="section-kicker">Data lineage</div>', unsafe_allow_html=True)
        st.code("Source → Python → Raw → dbt → Snowflake → Streamlit", language="text")
        st.caption("Queries are cached for 15 minutes to keep local exploration responsive and Snowflake usage modest.")
except Exception as exc:
    st.error(f"The overview could not load: {exc}")
