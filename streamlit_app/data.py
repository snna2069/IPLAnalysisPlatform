"""Read-only Snowflake access and shared UI helpers for the Streamlit app."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st


ANALYTICS_TABLES = {
    "matches": "IPL_ANALYTICS.ANALYTICS.FACT_MATCHES",
    "players": "IPL_ANALYTICS.ANALYTICS.DIM_PLAYER",
    "teams": "IPL_ANALYTICS.ANALYTICS.DIM_TEAM",
    "seasons": "IPL_ANALYTICS.ANALYTICS.DIM_SEASON",
    "venues": "IPL_ANALYTICS.ANALYTICS.DIM_VENUE",
    "performance": "IPL_ANALYTICS.ANALYTICS.FACT_PLAYER_PERFORMANCE",
    "deliveries": "IPL_ANALYTICS.ANALYTICS.FACT_DELIVERIES",
}


def _setting(name: str, default: Any = None) -> Any:
    """Read Streamlit secrets first, then environment variables."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except FileNotFoundError:
        pass
    return os.getenv(name, default)


@st.cache_resource(show_spinner=False)
def get_connection():
    """Create one read-only Snowflake connector per Streamlit process."""
    try:
        import snowflake.connector
    except ImportError as exc:
        raise RuntimeError("Install snowflake-connector-python to use Snowflake mode.") from exc

    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    missing = [name for name in required if not _setting(name)]
    if missing:
        raise RuntimeError(
            "Missing Snowflake settings: " + ", ".join(missing) + ". "
            "Set environment variables or configure .streamlit/secrets.toml."
        )
    return snowflake.connector.connect(
        account=_setting("SNOWFLAKE_ACCOUNT"),
        user=_setting("SNOWFLAKE_USER"),
        password=_setting("SNOWFLAKE_PASSWORD"),
        warehouse=_setting("SNOWFLAKE_WAREHOUSE", "IPL_ANALYTICS_WH"),
        database=_setting("SNOWFLAKE_DATABASE", "IPL_ANALYTICS"),
        schema=_setting("SNOWFLAKE_SCHEMA", "ANALYTICS"),
        role=_setting("SNOWFLAKE_ROLE"),
        session_parameters={"QUERY_TAG": "IPL_STREAMLIT_READ_ONLY"},
    )


@st.cache_data(ttl=900, show_spinner=False)
def query(sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    """Run a cached read-only query against the analytics schema."""
    if not sql.lstrip().lower().startswith("select"):
        raise ValueError("The Streamlit data layer only permits SELECT queries.")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.fetch_pandas_all()
    finally:
        cursor.close()


@st.cache_data(ttl=900, show_spinner=False)
def load_filter_options() -> dict[str, list[str]]:
    return {
        "seasons": _values("SELECT SEASON::VARCHAR AS VALUE FROM IPL_ANALYTICS.ANALYTICS.DIM_SEASON ORDER BY 1"),
        "teams": _values("SELECT TEAM_NAME AS VALUE FROM IPL_ANALYTICS.ANALYTICS.DIM_TEAM ORDER BY 1"),
        "players": _values("SELECT PLAYER_NAME AS VALUE FROM IPL_ANALYTICS.ANALYTICS.DIM_PLAYER ORDER BY 1"),
        "venues": _values("SELECT VENUE AS VALUE FROM IPL_ANALYTICS.ANALYTICS.DIM_VENUE ORDER BY 1"),
    }


def _values(sql: str) -> list[str]:
    frame = query(sql)
    return frame["VALUE"].dropna().astype(str).tolist() if "VALUE" in frame else []


def where_clause(
    season: str | None = None,
    team: str | None = None,
    player: str | None = None,
    venue: str | None = None,
    aliases: dict[str, str] | None = None,
) -> tuple[str, list[str]]:
    """Build parameterized filters for known analytics columns."""
    aliases = aliases or {}
    conditions: list[str] = []
    params: list[str] = []
    for value, key, default_column in (
        (season, "season", "f.season"),
        (team, "team", "f.team_1"),
        (player, "player", "p.player_name"),
        (venue, "venue", "f.venue"),
    ):
        if value and value != "All":
            conditions.append(f"{aliases.get(key, default_column)} = %s")
            params.append(value)
    return (" AND ".join(conditions) or "1=1", params)


def app_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background: #f4f0e8; }
        [data-testid="stSidebar"] { background: #172a3a; }
        [data-testid="stSidebar"] * { color: #f4f0e8; }
        .hero { background: #172a3a; color: #f4f0e8; padding: 2.2rem 2.4rem; border-radius: 0 0 18px 18px; margin: -1rem -1rem 1.5rem; }
        .hero h1 { color: #e9c46a; font-family: Georgia, serif; font-size: 3.2rem; margin: 0; }
        .hero p { max-width: 720px; color: #d9e2e8; font-size: 1.05rem; }
        .metric-card { background: #fffdf8; border-left: 4px solid #e76f51; padding: 1rem 1.1rem; border-radius: 8px; box-shadow: 0 4px 14px #172a3a12; }
        .section-kicker { color: #e76f51; font-size: .75rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
        div[data-testid="stMetric"] { background: #fffdf8; border-left: 4px solid #e9c46a; padding: .8rem; border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_filters(options: dict[str, list[str]] | None = None) -> dict[str, str]:
    options = options or load_filter_options()
    st.sidebar.markdown("## IPL Analytics")
    st.sidebar.caption("Snowflake analytics layer")
    return {
        "season": st.sidebar.selectbox("Season", ["All", *options.get("seasons", [])]),
        "team": st.sidebar.selectbox("Team", ["All", *options.get("teams", [])]),
        "player": st.sidebar.selectbox("Player", ["All", *options.get("players", [])]),
        "venue": st.sidebar.selectbox("Venue", ["All", *options.get("venues", [])]),
    }


def safe_options() -> dict[str, list[str]]:
    try:
        return load_filter_options()
    except Exception as exc:
        st.sidebar.error("Snowflake connection unavailable")
        st.error(f"Analytics data could not be loaded. Check Snowflake settings and permissions. Details: {exc}")
        st.stop()


def show_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="section-kicker">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
