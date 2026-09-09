import json
import zipfile

import pytest

from ingestion.load_to_snowflake import _dataset_name, _records, get_snowflake_config


def test_get_snowflake_config_requires_credentials(monkeypatch):
    for name in (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="Missing Snowflake environment variables"):
        get_snowflake_config()


def test_records_reads_json_members_from_zip(tmp_path):
    path = tmp_path / "matches.zip"
    payload = {"info": {"dates": ["2024-01-01"]}, "innings": []}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("match-1.json", json.dumps(payload))

    records = list(_records(path))

    assert records == [("match-1.json", payload)]


@pytest.mark.parametrize("filename, expected", [("matches.csv", "matches"), ("deliveries_2024.json", "deliveries")])
def test_dataset_name_maps_raw_files(filename, expected):
    from pathlib import Path

    assert _dataset_name(Path(filename)) == expected