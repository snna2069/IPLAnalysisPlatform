"""Contract tests that pin the Cricsheet JSON paths and the P0 regression fixes.

The dbt SQL cannot be executed locally (it needs Snowflake), so these tests assert
two things instead:

1. The fixtures really do use the Cricsheet 1.2.0 field names, so the expectations
   encoded in the dbt models are anchored to the documented source format.
2. The dbt and Streamlit source files still reference the corrected paths and
   still contain the deduplication guards, so the fixed defects cannot silently
   reappear.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from ingestion.config import IngestionConfig
from ingestion.fetch_ipl_data import _filename, fetch_dataset
from ingestion.load_to_snowflake import _dataset_name, _file_hash, _records
from ingestion.validate_raw_data import validate_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cricsheet"
DBT_MODELS = PROJECT_ROOT / "dbt" / "ipl_analytics" / "models"

STG_MATCHES = DBT_MODELS / "staging" / "stg_matches.sql"
STG_DELIVERIES = DBT_MODELS / "staging" / "stg_deliveries.sql"
TEAM_PAGE = PROJECT_ROOT / "streamlit_app" / "pages" / "1_Team_Analysis.py"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _all_fixtures() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text)


# --------------------------------------------------------------------------
# Cricsheet source contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", _all_fixtures(), ids=lambda p: p.stem)
def test_toss_uses_winner_not_won(path: Path) -> None:
    """F-02: Cricsheet spells the toss winner 'winner'; 'won' does not exist."""
    toss = json.loads(path.read_text(encoding="utf-8"))["info"]["toss"]
    assert "winner" in toss
    assert "won" not in toss
    assert toss["decision"] in {"bat", "field"}


@pytest.mark.parametrize("path", _all_fixtures(), ids=lambda p: p.stem)
def test_outcome_margin_lives_under_by_not_margin(path: Path) -> None:
    """F-01: Cricsheet nests the victory margin under 'by', never 'margin'."""
    outcome = json.loads(path.read_text(encoding="utf-8"))["info"]["outcome"]
    assert "margin" not in outcome
    if "by" in outcome:
        assert set(outcome["by"]) <= {"runs", "wickets", "innings"}


def test_fixtures_cover_the_outcome_edge_cases() -> None:
    """Normal win, D/L win, tie decided by super over, and no result."""
    by_runs = _fixture("match_win_by_runs.json")["info"]["outcome"]
    assert by_runs["by"]["runs"] == 31

    dl = _fixture("match_win_by_wickets_dl.json")["info"]["outcome"]
    assert dl["by"]["wickets"] == 6
    assert dl["method"] == "D/L"

    tie = _fixture("match_tie_super_over.json")["info"]["outcome"]
    assert tie["result"] == "tie"
    assert tie["eliminator"] == "Kings XI Punjab"
    assert "winner" not in tie

    no_result = _fixture("match_no_result.json")["info"]["outcome"]
    assert no_result["result"] == "no result"
    assert "winner" not in no_result
    assert "by" not in no_result


def test_super_over_innings_are_flagged_in_the_source() -> None:
    """F-16: super-over innings carry a flag that aggregation must respect."""
    innings = _fixture("match_tie_super_over.json")["innings"]
    assert [bool(entry.get("super_over")) for entry in innings] == [
        False,
        False,
        True,
        True,
    ]


def test_seasons_are_not_always_numeric() -> None:
    """F-15: split seasons such as '2007/08' break try_to_number ordering."""
    season = _fixture("match_win_by_wickets_dl.json")["info"]["season"]
    assert season == "2007/08"
    assert not season.isdigit()


# --------------------------------------------------------------------------
# dbt model regression guards
# --------------------------------------------------------------------------


def test_stg_matches_reads_the_documented_cricsheet_paths() -> None:
    """F-01 and F-02 must not reappear in the staging model."""
    sql = STG_MATCHES.read_text(encoding="utf-8")
    assert "info:toss:won" not in sql
    assert "outcome:margin" not in sql
    assert "info:toss:winner" in sql
    assert "outcome:by:runs" in sql
    assert "outcome:by:wickets" in sql
    assert "outcome:eliminator" in sql


def test_toss_decision_is_not_treated_as_a_team_name() -> None:
    """F-14: standardize_team must not be applied to the bat/field enum."""
    sql = _squash(STG_MATCHES.read_text(encoding="utf-8"))
    assert "standardize_team(\"raw_payload:info:toss:decision" not in sql
    assert "lower(nullif(trim(raw_payload:info:toss:decision::varchar), ''))" in sql


@pytest.mark.parametrize("model", [STG_MATCHES, STG_DELIVERIES], ids=lambda p: p.stem)
def test_staging_models_deduplicate_the_cumulative_archive(model: Path) -> None:
    """F-03: re-downloading the archive must not duplicate match records."""
    sql = _squash(model.read_text(encoding="utf-8")).lower()
    assert "qualify row_number() over ( partition by record_id" in sql


def test_margins_are_not_collapsed_to_zero() -> None:
    """F-01: a null margin means 'not applicable', not a margin of zero."""
    sql = _squash(
        (DBT_MODELS / "intermediate" / "int_match_results.sql").read_text(encoding="utf-8")
    )
    assert "coalesce(win_by_runs, 0)" not in sql
    assert "coalesce(win_by_wickets, 0)" not in sql
    assert "coalesce(winner, eliminator) as match_winner" in sql


def test_winner_side_is_null_safe() -> None:
    """F-05: an abandoned match must not silently report team_2 as the winner."""
    sql = _squash(
        (DBT_MODELS / "intermediate" / "int_match_results.sql").read_text(encoding="utf-8")
    )
    assert "iff(winner is not null and winner = team_1, team_1, team_2)" not in sql


# --------------------------------------------------------------------------
# Streamlit regression guard
# --------------------------------------------------------------------------


def test_team_page_does_not_join_dim_match() -> None:
    """F-04: joining DIM_MATCH to FACT_MATCHES made every shared column ambiguous."""
    page = TEAM_PAGE.read_text(encoding="utf-8")
    assert "DIM_MATCH" not in page
    assert "f.team_1 as team_name" in page


# --------------------------------------------------------------------------
# Ingestion behaviour against a realistic Cricsheet archive
# --------------------------------------------------------------------------


class _FakeSession:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls = 0

    def get(self, url, timeout):
        import requests

        self.calls += 1
        response = requests.Response()
        response.status_code = 200
        response._content = self.payload
        return response


def _archive_bytes() -> bytes:
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("README.txt", "Cricsheet archive notes\n")
        for fixture in _all_fixtures():
            archive.writestr(fixture.name, fixture.read_text(encoding="utf-8"))
    return buffer.getvalue()


def test_cricsheet_archive_maps_to_the_matches_dataset() -> None:
    """The documented source URL must resolve to the RAW_MATCHES table."""
    name = _filename("matches", "https://cricsheet.org/downloads/ipl_json.zip")
    assert name == "matches_ipl_json.zip"
    assert _dataset_name(Path(name)) == "matches"


def test_repeated_ingestion_is_byte_stable(tmp_path) -> None:
    """F-03: an unchanged archive must produce an identical file and hash."""
    payload = _archive_bytes()
    config = IngestionConfig(tmp_path / "raw", tmp_path / "metadata.json", {})
    session = _FakeSession(payload)
    url = "https://cricsheet.org/downloads/ipl_json.zip"

    first = fetch_dataset("matches", url, config, session)
    stored = tmp_path / "raw" / first["file_name"]
    first_hash = _file_hash(stored)

    second = fetch_dataset("matches", url, config, session)

    assert session.calls == 2
    assert second["file_name"] == first["file_name"]
    assert _file_hash(stored) == first_hash
    assert first["record_count"] == second["record_count"]


def test_archive_records_parse_into_match_payloads(tmp_path) -> None:
    """The loader must yield one JSON payload per match and skip non-JSON members."""
    path = tmp_path / "matches_ipl_json.zip"
    path.write_bytes(_archive_bytes())

    records = dict(_records(path))

    assert "README.txt" not in records
    assert len(records) == len(_all_fixtures())
    assert records["match_win_by_runs.json"]["info"]["toss"]["winner"] == "Chennai Super Kings"


def test_archive_passes_raw_validation(tmp_path) -> None:
    path = tmp_path / "matches_ipl_json.zip"
    path.write_bytes(_archive_bytes())
    assert validate_file(path) == []
