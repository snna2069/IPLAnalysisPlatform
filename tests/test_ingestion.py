import zipfile

import pandas as pd
import pytest
import requests

from ingestion.config import IngestionConfig
from ingestion.fetch_ipl_data import fetch_dataset
from ingestion.validate_raw_data import validate_file


def _response(payload: bytes) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = payload
    return response


class FakeSession:
    def __init__(self, payload: bytes):
        self.payload = payload

    def get(self, url, timeout):
        return _response(self.payload)


def test_fetch_dataset_preserves_bytes_and_writes_metadata(tmp_path):
    payload = b"match_id,team\n1,Royal Challengers Bengaluru\n"
    config = IngestionConfig(tmp_path / "raw", tmp_path / "processed", tmp_path / "metadata.json", {})

    metadata = fetch_dataset("matches", "https://example.test/matches.csv", config, FakeSession(payload))

    output = tmp_path / "raw" / "matches.csv"
    assert output.read_bytes() == payload
    assert metadata["record_count"] == 1
    assert metadata["file_name"] == output.name
    assert metadata["ingestion_timestamp"]


@pytest.mark.parametrize(
    "frame, expected",
    [
        (pd.DataFrame({"id": [1], "name": ["A"]}), []),
        (pd.DataFrame({"id": [1, 1]}), ["completely duplicate records found"]),
    ],
)
def test_validate_file_checks_duplicates_and_columns(tmp_path, frame, expected):
    path = tmp_path / "players.csv"
    frame.to_csv(path, index=False)
    assert validate_file(path, ["id"]) == expected


def test_validate_file_reports_missing_columns(tmp_path):
    path = tmp_path / "teams.csv"
    path.write_text("id\n1\n", encoding="utf-8")
    assert "missing required columns: ['name']" in validate_file(path, ["name"])


def test_validate_file_reports_missing_and_empty_files(tmp_path):
    assert validate_file(tmp_path / "missing.csv") == ["file does not exist"]
    empty = tmp_path / "empty.csv"
    empty.touch()
    assert validate_file(empty) == ["file is empty"]


def test_validate_file_accepts_nonempty_zip_sources(tmp_path):
    path = tmp_path / "matches.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("match-1.json", b"{}")
    assert validate_file(path) == []