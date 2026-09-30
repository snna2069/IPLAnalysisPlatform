"""Reliability tests for Phase B: idempotency, validation depth, and batched loading."""

from __future__ import annotations

import ast
import json
import zipfile
from pathlib import Path

import pytest

from ingestion.config import IngestionConfig, dataset_from_filename, file_sha256
from ingestion.fetch_ipl_data import _record_count, fetch_dataset
from ingestion.load_to_snowflake import LOAD_BATCH_SIZE, _flush_batch, insert_statement
from ingestion.validate_raw_data import validate_file
from tests.conftest import PROJECT_ROOT, FakeSession

SOURCE_URL = "https://cricsheet.org/downloads/ipl_json.zip"
DAG_FILE = PROJECT_ROOT / "airflow" / "dags" / "ipl_pipeline_dag.py"


def _config(tmp_path: Path) -> IngestionConfig:
    return IngestionConfig(tmp_path / "raw", tmp_path / "raw" / "metadata.json", {})


# --------------------------------------------------------------------------
# Dataset resolution shared by validation and loading (F-26)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("matches.csv", "matches"),
        ("matches_ipl_json.zip", "matches"),
        ("deliveries_2024.json", "deliveries"),
        ("players.json", "players"),
        ("teams.csv", "teams"),
        ("unrelated_file.csv", None),
    ],
)
def test_dataset_resolution_handles_prefixed_downloads(filename: str, expected: str | None) -> None:
    assert dataset_from_filename(Path(filename)) == expected


def test_required_columns_are_checked_against_archive_contents(tmp_path: Path, match_payload: dict) -> None:
    """Required columns must be matched against real JSON keys, not the file list."""
    path = tmp_path / "matches_ipl_json.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("match-1.json", json.dumps(match_payload))

    assert validate_file(path, ["meta", "info", "innings"]) == []
    assert "missing required columns: ['scorecard']" in validate_file(path, ["scorecard"])


# --------------------------------------------------------------------------
# Archive validation depth (F-27)
# --------------------------------------------------------------------------


def test_validation_rejects_a_corrupt_json_member(tmp_path: Path) -> None:
    """Listing member names could not detect this; the member must be decoded."""
    path = tmp_path / "matches.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("match-1.json", "{not valid json")

    errors = validate_file(path)

    assert errors and "unable to read data" in errors[0]


def test_validation_rejects_an_archive_with_no_json_members(tmp_path: Path) -> None:
    path = tmp_path / "matches.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("README.txt", "notes only")

    assert validate_file(path) == ["unable to read data: archive contains no JSON members"]


def test_validation_rejects_a_truncated_archive(tmp_path: Path, cricsheet_archive: bytes) -> None:
    path = tmp_path / "matches.zip"
    path.write_bytes(cricsheet_archive[: len(cricsheet_archive) // 2])

    errors = validate_file(path)

    assert errors and "unable to read data" in errors[0]


# --------------------------------------------------------------------------
# Ingestion integrity (F-29, F-40, F-43)
# --------------------------------------------------------------------------


def test_metadata_records_the_file_hash(tmp_path: Path, cricsheet_archive: bytes) -> None:
    config = _config(tmp_path)

    metadata = fetch_dataset("matches", SOURCE_URL, config, FakeSession(cricsheet_archive))

    stored = config.raw_dir / metadata["file_name"]
    assert metadata["file_hash"] == file_sha256(stored)
    assert len(metadata["file_hash"]) == 64


def test_record_count_ignores_non_json_archive_members(
    tmp_path: Path, cricsheet_archive: bytes, cricsheet_fixtures: list[Path]
) -> None:
    """The archive also contains README.txt, which the loader never inserts."""
    config = _config(tmp_path)

    metadata = fetch_dataset("matches", SOURCE_URL, config, FakeSession(cricsheet_archive))

    assert metadata["record_count"] == len(cricsheet_fixtures)


def test_failed_download_leaves_no_file_in_the_raw_zone(tmp_path: Path) -> None:
    """An unreadable payload must not leave a partial file for downstream tasks."""
    config = _config(tmp_path)

    with pytest.raises(ValueError):
        fetch_dataset("matches", "https://example.test/matches.bin", config, FakeSession(b"junk"))

    assert list(config.raw_dir.glob("*")) == []


def test_reingestion_replaces_rather_than_appends(tmp_path: Path, cricsheet_archive: bytes) -> None:
    config = _config(tmp_path)
    session = FakeSession(cricsheet_archive)

    first = fetch_dataset("matches", SOURCE_URL, config, session)
    second = fetch_dataset("matches", SOURCE_URL, config, session)

    assert first["file_hash"] == second["file_hash"]
    assert [p.name for p in sorted(config.raw_dir.glob("*"))] == [first["file_name"]]


def test_record_count_uses_the_intended_suffix_for_staging_files(tmp_path: Path) -> None:
    """Counting happens before the atomic swap, while the file is still *.part."""
    staged = tmp_path / "matches_ipl_json.zip.part"
    with zipfile.ZipFile(staged, "w") as archive:
        archive.writestr("match-1.json", "{}")

    assert _record_count(staged, ".zip") == 1


# --------------------------------------------------------------------------
# Batched Snowflake loading (F-44)
# --------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self) -> None:
        self.statements: list[tuple[str, list]] = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))


def test_insert_statement_binds_one_tuple_per_row() -> None:
    sql = insert_statement("RAW_MATCHES", 3)

    assert sql.count("(%s, %s, %s, %s, %s)") == 3
    assert "PARSE_JSON(column4)" in sql
    assert "FROM VALUES" in sql


def test_insert_statement_rejects_an_empty_batch() -> None:
    with pytest.raises(ValueError):
        insert_statement("RAW_MATCHES", 0)


def test_flush_batch_sends_a_single_statement() -> None:
    """The previous implementation issued one round trip per delivery."""
    cursor = _FakeCursor()
    rows = [(str(index), "f.zip", "hash", "{}", None) for index in range(4)]

    written = _flush_batch(cursor, "RAW_MATCHES", rows)

    assert written == 4
    assert len(cursor.statements) == 1
    assert len(cursor.statements[0][1]) == 20


def test_flush_batch_is_a_no_op_when_empty() -> None:
    cursor = _FakeCursor()

    assert _flush_batch(cursor, "RAW_MATCHES", []) == 0
    assert cursor.statements == []


def test_batch_size_is_within_snowflake_bind_limits() -> None:
    assert 1 < LOAD_BATCH_SIZE * 5 <= 16384


# --------------------------------------------------------------------------
# Orchestration structure (F-42)
# --------------------------------------------------------------------------


def test_dag_module_is_syntactically_valid() -> None:
    ast.parse(DAG_FILE.read_text(encoding="utf-8"))


def test_dag_sets_execution_timeouts() -> None:
    source = DAG_FILE.read_text(encoding="utf-8")

    assert '"execution_timeout": timedelta(minutes=60)' in source
    assert "execution_timeout=timedelta(minutes=120)" in source


def test_dag_keeps_a_linear_ordered_task_chain() -> None:
    source = DAG_FILE.read_text(encoding="utf-8")

    assert (
        "start >> ingest_data >> validate_data_task >> load_to_snowflake_task "
        ">> dbt_run >> dbt_test >> pipeline_success"
    ) in source


def test_compose_keeps_dbt_and_loader_schemas_separate() -> None:
    """Sharing SNOWFLAKE_SCHEMA sent dbt test artifacts into the raw zone."""
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    profiles = (
        PROJECT_ROOT / "dbt" / "ipl_analytics" / "profiles.yml"
    ).read_text(encoding="utf-8")

    assert "DBT_TARGET_SCHEMA" in compose
    assert "env_var('DBT_TARGET_SCHEMA', 'ANALYTICS')" in profiles
    assert "env_var('SNOWFLAKE_SCHEMA'" not in profiles


def test_airflow_init_does_not_mask_migration_failure() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "|| true" not in compose
    assert "set -e" in compose
