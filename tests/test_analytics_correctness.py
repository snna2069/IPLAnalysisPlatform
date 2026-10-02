"""Execute model arithmetic and page queries locally, not Snowflake JSON syntax."""

from __future__ import annotations

import re
import runpy
import sqlite3
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "dbt" / "ipl_analytics" / "models"


class CountIf:
    def __init__(self) -> None:
        self.count = 0

    def step(self, condition: object) -> None:
        self.count += int(bool(condition))

    def finalize(self) -> int | None:
        return self.count or None


@pytest.fixture
def db():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.create_function(
        "iff", 3, lambda condition, yes, no: yes if condition else no
    )
    connection.create_function("try_to_number", 1, lambda value: int(value))
    connection.create_aggregate("count_if", 1, CountIf)
    yield connection
    connection.close()


def _key(columns: list[str]) -> str:
    return " || '-' || ".join(
        f"coalesce(cast({c} as text), '__null__')" for c in columns
    )


def _render(path: Path) -> str:
    return (
        Environment(undefined=StrictUndefined)
        .from_string(path.read_text(encoding="utf-8"))
        .render(
            config=lambda **kwargs: "",
            ref=lambda name: name,
            dbt_utils=SimpleNamespace(generate_surrogate_key=_key),
        )
    )


def _model(db: sqlite3.Connection, relative: str) -> None:
    path = MODELS / relative
    db.execute(f"create table {path.stem} as {_render(path)}")


def _table(db: sqlite3.Connection, name: str, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_sql(name, db, index=False)


def _delivery(**overrides: object) -> dict:
    row = {
        "delivery_id": "d1",
        "match_id": "m1",
        "innings_number": 0,
        "over_number": 0,
        "ball_number": 0,
        "batting_team": "A",
        "is_super_over": False,
        "batter": "Batter",
        "bowler": "Bowler",
        "non_striker": "Non-striker",
        "batter_runs": 0.0,
        "extra_runs": 0.0,
        "total_runs": 0.0,
        "wides": 0,
        "no_balls": 0,
        "byes": 0,
        "leg_byes": 0,
        "penalty_runs": 0,
        "player_out": None,
        "dismissal_kind": None,
        "is_non_boundary": False,
        "team_wickets": 0,
        "bowler_wickets": 0,
        "source_file": "fixture",
        "file_hash": "hash",
        "loaded_at": "2024-01-01",
    }
    row.update(overrides)
    return row


def _performance(db: sqlite3.Connection, deliveries: list[dict]) -> None:
    _table(db, "stg_deliveries", deliveries)
    _model(db, r"intermediate\int_match_deliveries.sql")
    _model(db, r"intermediate\int_player_match_performance.sql")
    _model(db, r"marts\fact_player_performance.sql")
    _model(db, r"marts\fact_deliveries.sql")


@pytest.mark.parametrize(
    "overrides, faced, legal, conceded, fours, sixes",
    [
        ({"batter_runs": 4.0, "total_runs": 4.0}, 1, 1, 4, 1, 0),
        ({"wides": 2, "extra_runs": 2.0, "total_runs": 2.0}, 0, 0, 2, 0, 0),
        (
            {"no_balls": 1, "batter_runs": 4.0, "extra_runs": 1.0, "total_runs": 5.0},
            1,
            0,
            5,
            1,
            0,
        ),
        ({"byes": 4, "extra_runs": 4.0, "total_runs": 4.0}, 1, 1, 0, 0, 0),
        ({"leg_byes": 2, "extra_runs": 2.0, "total_runs": 2.0}, 1, 1, 0, 0, 0),
        ({"penalty_runs": 5, "extra_runs": 5.0, "total_runs": 5.0}, 1, 1, 0, 0, 0),
        (
            {"no_balls": 1, "byes": 2, "extra_runs": 3.0, "total_runs": 3.0},
            1,
            0,
            1,
            0,
            0,
        ),
        ({"batter_runs": 5.0, "total_runs": 5.0}, 1, 1, 5, 0, 0),
        (
            {"batter_runs": 4.0, "total_runs": 4.0, "is_non_boundary": True},
            1,
            1,
            4,
            0,
            0,
        ),
        (
            {"batter_runs": 6.0, "total_runs": 6.0, "is_non_boundary": True},
            1,
            1,
            6,
            0,
            0,
        ),
        ({"batter_runs": 6.0, "total_runs": 6.0}, 1, 1, 6, 0, 1),
    ],
)
def test_delivery_rules_execute_actual_models(
    db, overrides, faced, legal, conceded, fours, sixes
) -> None:
    _performance(db, [_delivery(**overrides)])
    batter = db.execute(
        "select * from fact_player_performance where player_name = 'Batter'"
    ).fetchone()
    bowler = db.execute(
        "select * from fact_player_performance where player_name = 'Bowler'"
    ).fetchone()
    assert (batter["balls_faced"], batter["fours"], batter["sixes"]) == (
        faced,
        fours,
        sixes,
    )
    assert (bowler["balls_bowled"], bowler["runs_conceded"]) == (legal, conceded)
    assert bowler["bowling_average"] is None


@pytest.mark.parametrize(
    "kinds, team, bowler",
    [
        ([], 0, 0),
        (["bowled"], 1, 1),
        (["caught"], 1, 1),
        (["caught and bowled"], 1, 1),
        (["lbw"], 1, 1),
        (["stumped"], 1, 1),
        (["hit wicket"], 1, 1),
        (["run out"], 1, 0),
        (["retired hurt"], 0, 0),
        (["retired out"], 1, 0),
        (["obstructing the field"], 1, 0),
        (["run out", "retired hurt"], 1, 0),
        (["caught", "retired out"], 2, 1),
    ],
)
def test_all_dismissals_use_actual_staging_count_expressions(
    db, kinds, team, bowler
) -> None:
    sql = (MODELS / r"staging\stg_deliveries.sql").read_text(encoding="utf-8")
    expressions = []
    counts_sql = re.findall(
        r"count_if\((.*?)\) as (team_wickets|bowler_wickets)", sql, re.DOTALL
    )
    assert [alias for _, alias in counts_sql] == ["team_wickets", "bowler_wickets"]
    for expression, _ in counts_sql:
        expressions.append(
            "coalesce(count_if("
            + expression.replace("w.value:kind::varchar", "kind")
            + "), 0)"
        )
    db.execute("create table wickets (kind text)")
    db.executemany("insert into wickets values (?)", [(k,) for k in kinds or [None]])
    counts = db.execute(f"select {', '.join(expressions)} from wickets").fetchone()
    assert tuple(counts) == (team, bowler)
    _performance(db, [_delivery(team_wickets=team, bowler_wickets=bowler)])
    delivery = db.execute(
        "select is_wicket, bowler_wickets from fact_deliveries"
    ).fetchone()
    assert tuple(delivery) == (team, bowler)
    actual = db.execute(
        "select wickets from fact_player_performance where player_name = 'Bowler'"
    ).fetchone()[0]
    assert actual == bowler


def test_super_overs_retained_but_excluded_from_player_totals_and_rates(db) -> None:
    _performance(
        db,
        [
            _delivery(batter_runs=4.0, total_runs=4.0),
            _delivery(delivery_id="d2", wides=1, extra_runs=1.0, total_runs=1.0),
            _delivery(
                delivery_id="d3",
                no_balls=1,
                batter_runs=2.0,
                extra_runs=1.0,
                total_runs=3.0,
            ),
            _delivery(delivery_id="d4", team_wickets=1, bowler_wickets=1),
            _delivery(
                delivery_id="d5",
                is_super_over=True,
                batter_runs=6.0,
                total_runs=6.0,
                team_wickets=1,
                bowler_wickets=1,
            ),
            _delivery(delivery_id="d6", is_super_over=True, batter="Super-only"),
        ],
    )
    rows = {
        r["player_name"]: r for r in db.execute("select * from fact_player_performance")
    }
    assert set(rows) == {"Batter", "Bowler"}
    assert rows["Batter"]["runs_scored"] == 6
    assert rows["Batter"]["balls_faced"] == 3
    assert rows["Batter"]["strike_rate"] == 200
    assert rows["Bowler"]["runs_conceded"] == 8
    assert rows["Bowler"]["balls_bowled"] == 2
    assert rows["Bowler"]["wickets"] == 1
    assert rows["Bowler"]["bowling_average"] == 8
    assert db.execute("select count(*) from fact_deliveries").fetchone()[0] == 6


def _match(**overrides: object) -> dict:
    row = {
        "match_id": "m1",
        "season": "2024",
        "event_stage": None,
        "match_date": "2024-05-01",
        "venue": "Venue",
        "team_1": "A",
        "team_2": "B",
        "winner": "A",
        "eliminator": None,
        "match_winner": "A",
        "toss_winner": "B",
        "toss_decision": "field",
        "result_type": "win",
        "result_method": None,
        "win_by_runs": 10,
        "win_by_wickets": None,
        "source_file": "fixture",
        "loaded_at": "2024-01-01",
    }
    row.update(overrides)
    return row


def _match_marts(db: sqlite3.Connection, matches: list[dict]) -> None:
    _table(db, "int_match_results", matches)
    _model(db, r"marts\fact_matches.sql")
    _model(db, r"marts\dim_match.sql")
    _model(db, r"marts\bridge_match_team.sql")
    db.execute(
        "create table dim_season as select distinct season as season_key, season from int_match_results"
    )
    _model(db, r"marts\fact_season_results.sql")


def test_team_bridge_and_winner_key_handle_ties_and_no_results(db) -> None:
    _match_marts(
        db,
        [
            _match(),
            _match(
                match_id="m2",
                winner=None,
                match_winner="B",
                eliminator="B",
                result_type="tie",
            ),
            _match(
                match_id="m3", winner=None, match_winner=None, result_type="no result"
            ),
            _match(match_id="m4", winner=None, match_winner=None, result_type="tie"),
        ],
    )
    counts = db.execute(
        "select match_id, count(*), sum(is_win) from bridge_match_team group by match_id"
    ).fetchall()
    assert [tuple(r) for r in counts] == [
        ("m1", 2, 1),
        ("m2", 2, 1),
        ("m3", 2, 0),
        ("m4", 2, 0),
    ]
    keys = {
        r["match_id"]: r["winner_key"] for r in db.execute("select * from fact_matches")
    }
    assert keys == {"m1": "A", "m2": "B", "m3": None, "m4": None}


@pytest.mark.parametrize(
    "matches, champion, final_id",
    [
        ([_match(event_stage="final", match_winner="B")], "B", "m1"),
        (
            [
                _match(
                    event_stage="final", winner=None, eliminator="B", match_winner="B"
                )
            ],
            "B",
            "m1",
        ),
        ([_match(event_stage="qualifier")], None, None),
        ([_match(event_stage="final", winner=None, match_winner=None)], None, None),
        (
            [_match(event_stage="final"), _match(match_id="m2", event_stage="final")],
            None,
            None,
        ),
        (
            [
                _match(),
                _match(match_id="m2"),
                _match(match_id="m3", event_stage="final", match_winner="B"),
            ],
            "B",
            "m3",
        ),
    ],
)
def test_champion_requires_unique_explicit_resolved_final(
    db, matches, champion, final_id
) -> None:
    _match_marts(db, matches)
    actual = db.execute(
        "select champion, final_match_id from fact_season_results"
    ).fetchone()
    assert tuple(actual) == (champion, final_id)


class FakeStreamlit(ModuleType):
    def __init__(self, selected_team: str = "All") -> None:
        super().__init__("streamlit")
        self.metrics: dict[str, object] = {}
        self.selected_team = selected_team

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def columns(self, count):
        return [self] * (count if isinstance(count, int) else len(count))

    def metric(self, name, value):
        self.metrics[name] = value

    def selectbox(self, *args):
        return self.selected_team

    def error(self, message):
        pytest.fail(message)

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def _page(monkeypatch, db, filename, filters, selected_team="All"):
    st = FakeStreamlit(selected_team)
    data = ModuleType("streamlit_app.data")
    results = []

    def query(sql, params=()):
        sql = sql.replace("IPL_ANALYTICS.ANALYTICS.", "").replace("%s", "?")
        cursor = db.execute(sql, params)
        frame = pd.DataFrame(
            cursor.fetchall(), columns=[c[0].upper() for c in cursor.description]
        )
        results.append(frame)
        return frame

    data.query = query
    data.app_css = lambda: None
    data.safe_options = dict
    data.show_header = lambda *args: None
    data.sidebar_filters = lambda options: filters
    monkeypatch.setitem(sys.modules, "streamlit", st)
    monkeypatch.setitem(sys.modules, "streamlit_app.data", data)
    runpy.run_path(str(ROOT / "streamlit_app" / "pages" / filename))
    return st, results


@pytest.fixture
def warehouse(db):
    _match_marts(
        db,
        [
            _match(),
            _match(
                match_id="m2",
                event_stage="final",
                venue="Other",
                winner=None,
                eliminator="B",
                match_winner="B",
                result_type="tie",
            ),
            _match(match_id="m3", season="2023", match_winner="A"),
        ],
    )
    _performance(
        db,
        [
            _delivery(batter="Alice", bowler="Bob", batter_runs=4.0, total_runs=4.0),
            _delivery(
                delivery_id="d2",
                match_id="m2",
                batter="Alice",
                bowler="Bob",
                batter_runs=6.0,
                total_runs=6.0,
            ),
            _delivery(
                delivery_id="d3",
                match_id="m2",
                batter="Alice",
                bowler="Bob",
                is_super_over=True,
                batter_runs=6.0,
                total_runs=6.0,
            ),
        ],
    )
    # Mirror the bridge output to test consumer SQL; Snowflake FLATTEN requires live dbt.
    _table(
        db,
        "bridge_player_match_team",
        [
            {
                "match_key": "m1",
                "player_key": "Alice",
                "player_name": "Alice",
                "team_name": "A",
            },
            {
                "match_key": "m1",
                "player_key": "Bob",
                "player_name": "Bob",
                "team_name": "B",
            },
            {
                "match_key": "m1",
                "player_key": "Fielder",
                "player_name": "Fielder",
                "team_name": "A",
            },
            {
                "match_key": "m2",
                "player_key": "Alice",
                "player_name": "Alice",
                "team_name": "B",
            },
            {
                "match_key": "m2",
                "player_key": "Bob",
                "player_name": "Bob",
                "team_name": "A",
            },
        ],
    )
    return db


@pytest.mark.parametrize("team, runs", [("A", 4), ("B", 6)])
def test_player_page_team_filter_tracks_representation_not_opponents(
    monkeypatch, warehouse, team, runs
):
    _, results = _page(
        monkeypatch,
        warehouse,
        "2_Player_Analysis.py",
        {"season": "2024", "team": team, "venue": "All", "player": "Alice"},
    )
    assert results[0]["PLAYER_NAME"].tolist() == ["Alice"]
    assert results[0]["RUNS"].tolist() == [runs]


def test_season_page_filters_performers_without_redefining_champion(
    monkeypatch, warehouse
):
    st, results = _page(
        monkeypatch,
        warehouse,
        "4_Season_Analysis.py",
        {"season": "2024", "team": "A", "venue": "Venue", "player": "Alice"},
    )
    assert st.metrics["Champion"] == "B"
    assert results[0]["RUNS"].tolist() == [4]
    assert results[2]["PLAYER_NAME"].tolist() == ["Alice"]
    assert results[2]["RUNS"].tolist() == [4]


def test_season_totals_exclude_super_overs_and_no_single_champion_for_all(
    monkeypatch, warehouse
):
    st, results = _page(
        monkeypatch,
        warehouse,
        "4_Season_Analysis.py",
        {"season": "All", "team": "All", "venue": "All", "player": "All"},
    )
    assert st.metrics["Champion"] == "Select one season"
    assert results[0].set_index("SEASON").loc["2024", "RUNS"] == 10


def test_head_to_head_keeps_sidebar_filters(monkeypatch, warehouse):
    _, results = _page(
        monkeypatch,
        warehouse,
        "1_Team_Analysis.py",
        {"season": "2024", "team": "A", "venue": "Venue", "player": "Fielder"},
        selected_team="A",
    )
    assert results[1]["MATCHES"].tolist() == [1]
    assert results[1]["TEAM_WINS"].tolist() == [1]


def test_match_page_uses_roster_and_excludes_super_over_scoring(monkeypatch, warehouse):
    _, results = _page(
        monkeypatch,
        warehouse,
        "3_Match_Analysis.py",
        {"season": "2024", "team": "All", "venue": "All", "player": "Alice"},
    )
    assert results[0]["WINNER"].tolist() == ["A", "B"]
    assert sorted(results[1]["TOTAL_RUNS"].tolist()) == [4, 6]


def test_roster_and_final_metadata_are_read_from_deduplicated_matches():
    staging = (MODELS / r"staging\stg_matches.sql").read_text(encoding="utf-8")
    assert "raw_payload:info:event:stage::varchar" in staging
    assert "raw_payload:info:players as player_roster" in staging
    bridge = (MODELS / r"marts\bridge_player_match_team.sql").read_text(
        encoding="utf-8"
    )
    assert "ref('stg_matches')" in bridge
    assert "lateral flatten(input => m.player_roster)" in bridge
    assert "standardize_team('t.key::varchar')" in bridge
    assert "lateral flatten(input => t.value)" in bridge


def test_match_result_winner_side_uses_super_over_decider(db):
    rows = [
        _match(winner=None, eliminator="B", match_winner="B", result_type="tie"),
        _match(match_id="m2", winner=None, match_winner=None, result_type="no result"),
    ]
    for row in rows:
        row["file_hash"] = "hash"
    _table(db, "stg_matches", rows)
    _model(db, r"intermediate\int_match_results.sql")
    results = db.execute(
        "select match_id, match_winner, winner_side from int_match_results order by match_id"
    ).fetchall()
    assert [tuple(r) for r in results] == [("m1", "B", "B"), ("m2", None, None)]


def test_season_page_missing_final_is_explicitly_unavailable(monkeypatch, warehouse):
    st, _ = _page(
        monkeypatch,
        warehouse,
        "4_Season_Analysis.py",
        {"season": "2023", "team": "All", "venue": "All", "player": "All"},
    )
    assert st.metrics["Champion"] == "Not available"


@pytest.mark.parametrize(
    "filename",
    [
        "1_Team_Analysis.py",
        "2_Player_Analysis.py",
        "3_Match_Analysis.py",
        "4_Season_Analysis.py",
    ],
)
def test_page_queries_accept_empty_filter_results(monkeypatch, warehouse, filename):
    st, results = _page(
        monkeypatch,
        warehouse,
        filename,
        {"season": "2024", "team": "All", "venue": "All", "player": "Unknown"},
    )
    assert results[0].empty
    assert st.metrics == {}


@pytest.mark.parametrize(
    "metric", ["runs_scored", "balls_faced", "wickets", "runs_conceded", "balls_bowled"]
)
def test_dbt_reconciliation_detects_each_metric_drift(warehouse, metric):
    sql = _render(
        ROOT
        / "dbt"
        / "ipl_analytics"
        / "tests"
        / "assert_player_performance_reconciliation.sql"
    )
    assert warehouse.execute(sql).fetchall() == []
    warehouse.execute(
        f"update fact_player_performance set {metric} = {metric} + 1 "
        "where match_id = 'm1' and player_name = 'Alice'"
    )
    assert [r[0] for r in warehouse.execute(sql)] == ["m1"]


@pytest.mark.parametrize(
    "defect", ["missing-team", "wrong-roster-team", "missing-player"]
)
def test_dbt_participation_guard_detects_bridge_defects(warehouse, defect):
    warehouse.execute("alter table bridge_player_match_team add column team_key text")
    warehouse.execute(
        "alter table bridge_player_match_team add column player_match_key text"
    )
    warehouse.execute(
        "update bridge_player_match_team "
        "set team_key = team_name, player_match_key = match_key || '-' || player_key"
    )
    sql = _render(
        ROOT / "dbt" / "ipl_analytics" / "tests" / "assert_participation_integrity.sql"
    )
    assert warehouse.execute(sql).fetchall() == []
    if defect == "missing-team":
        warehouse.execute(
            "delete from bridge_match_team where match_id = 'm1' and team_name = 'B'"
        )
    elif defect == "wrong-roster-team":
        warehouse.execute(
            "update bridge_player_match_team set team_key = 'C' where player_name = 'Fielder'"
        )
    else:
        warehouse.execute(
            "delete from bridge_player_match_team where match_key = 'm1' and player_name = 'Alice'"
        )
    assert "m1" in [r[0] for r in warehouse.execute(sql)]
