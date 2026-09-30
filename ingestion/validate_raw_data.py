"""Basic validation for files in the IPL raw data zone."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.config import dataset_from_filename, get_config


def _archive_frame(path: Path) -> pd.DataFrame:
    """Describe each JSON member of an archive as one row.

    Cricsheet ships one JSON object per match, so this parses every member rather
    than trusting the file listing: a truncated download or a corrupted member is
    only detectable by decoding it.
    """
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        json_members = [name for name in members if name.lower().endswith(".json")]
        if not json_members:
            raise ValueError("archive contains no JSON members")
        rows = []
        for name in json_members:
            payload: Any = json.loads(archive.read(name).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"{name} does not contain a JSON object")
            row: dict[str, Any] = {"file_name": name}
            row.update({key: True for key in payload})
            rows.append(row)
    return pd.DataFrame(rows)


def _as_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".json":
        value: Any = json.loads(path.read_text(encoding="utf-8"))
        records = value if isinstance(value, list) else value.get("data", value)
        return pd.json_normalize(records if isinstance(records, list) else [records])
    if path.suffix.lower() == ".zip":
        return _archive_frame(path)
    raise ValueError(f"Validation supports CSV, JSON, and ZIP files, not {path.suffix}")


def validate_file(path: Path, required_columns: list[str] | None = None) -> list[str]:
    """Return validation errors; an empty list means the file is valid."""
    if not path.exists():
        return ["file does not exist"]
    if path.stat().st_size == 0:
        return ["file is empty"]
    try:
        frame = _as_frame(path)
    except (
        ValueError,
        json.JSONDecodeError,
        pd.errors.ParserError,
        zipfile.BadZipFile,
        UnicodeDecodeError,
    ) as exc:
        return [f"unable to read data: {exc}"]
    errors = []
    if frame.empty:
        errors.append("data is empty")
    missing = set(required_columns or ()) - set(frame.columns)
    if missing:
        errors.append(f"missing required columns: {sorted(missing)}")
    if frame.duplicated().any():
        errors.append("completely duplicate records found")
    return errors


def validate_raw_data() -> dict[str, list[str]]:
    config = get_config()
    paths = sorted(config.raw_dir.iterdir()) if config.raw_dir.exists() else []
    results: dict[str, list[str]] = {}
    for path in paths:
        if not path.is_file() or path.name == config.metadata_file.name:
            continue
        # Required columns are configured per dataset ("matches") while the stored
        # file is prefixed ("matches_ipl_json.zip"), so resolve the dataset first.
        dataset = dataset_from_filename(path) or path.stem
        results[str(path)] = validate_file(path, config.required_columns.get(dataset, []))
    return results


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    results = validate_raw_data()
    print(json.dumps(results, indent=2))
    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())