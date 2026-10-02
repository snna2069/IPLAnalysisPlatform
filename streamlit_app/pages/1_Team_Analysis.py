from __future__ import annotations

import streamlit as st

from streamlit_app.data import app_css, query, safe_options, show_header, sidebar_filters


st.set_page_config(page_title="Team Analysis | IPL Analytics", page_icon="🏆", layout="wide")
app_css()
filters = sidebar_filters(safe_options())
show_header("TEAM ANALYSIS", "Dynasties, rivalries, momentum.", "Compare team outcomes across the seasons and find the matchups that shaped the league.")

season = filters["season"]
team = filters["team"]
venue = filters["venue"]
params = []
conditions = ["1=1"]
if season != "All":
    conditions.append("f.season = %s")
    params.append(season)
if venue != "All":
    conditions.append("f.venue = %s")
    params.append(venue)
if team != "All":
    conditions.append("(f.team_1 = %s or f.team_2 = %s)")
    params.extend([team, team])
if filters["player"] != "All":
    conditions.append("exists (select 1 from IPL_ANALYTICS.ANALYTICS.BRIDGE_PLAYER_MATCH_TEAM r where r.match_key = f.match_key and r.player_name = %s)")
    params.append(filters["player"])
where = " AND ".join(conditions)

try:
    team_stats = query(
        f"""
        with participation as (
            select b.team_name, b.match_key, b.is_win
            from IPL_ANALYTICS.ANALYTICS.FACT_MATCHES f
            join IPL_ANALYTICS.ANALYTICS.BRIDGE_MATCH_TEAM b using (match_key)
            where {where}
        )
         select team_name, matches_played, wins,
             round(100 * wins / nullif(matches_played, 0), 1) as win_percentage
         from (
             select team_name, count(distinct match_key) as matches_played,
                 sum(is_win) as wins
             from participation
             group by team_name
         ) stats
         order by wins desc
        """,
        tuple(params),
    )
    if team_stats.empty:
        st.info("No team results match the selected filters.")
    else:
        kpi = st.columns(3)
        kpi[0].metric("Leading team", team_stats.iloc[0]["TEAM_NAME"])
        kpi[1].metric("Most wins", int(team_stats.iloc[0]["WINS"]))
        best_win_rate = team_stats["WIN_PERCENTAGE"].max()
        kpi[2].metric("Best win rate", f"{best_win_rate:.1f}%")
        left, right = st.columns(2)
        with left:
            st.subheader("Wins by team")
            st.bar_chart(team_stats.set_index("TEAM_NAME")["WINS"], color="#e76f51")
        with right:
            st.subheader("Win percentage")
            st.bar_chart(team_stats.set_index("TEAM_NAME")["WIN_PERCENTAGE"], color="#2a9d8f")
        st.subheader("Team comparison")
        st.dataframe(team_stats, use_container_width=True, hide_index=True)

        st.subheader("Head-to-head")
        selected_team = st.selectbox("Choose a team", ["All", *team_stats["TEAM_NAME"].tolist()])
        if selected_team != "All":
            h2h = query(
                f"""
                select b.opponent,
                       count(*) as matches,
                       sum(b.is_win) as team_wins
                from IPL_ANALYTICS.ANALYTICS.BRIDGE_MATCH_TEAM b
                join IPL_ANALYTICS.ANALYTICS.FACT_MATCHES f using (match_key)
                where {where} and b.team_name = %s
                group by b.opponent order by team_wins desc
                """,
                (*params, selected_team),
            )
            st.dataframe(h2h, use_container_width=True, hide_index=True)
        st.caption("Wins include super-over deciders. Win percentage uses all matches played, including ties and no-results. Head-to-head respects the same sidebar filters.")
except Exception as exc:
    st.error(f"Team analysis could not load: {exc}")
