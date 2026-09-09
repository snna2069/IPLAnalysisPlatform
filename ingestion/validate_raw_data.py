"""Basic validation for files in the IPL raw data zone."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.config import get_config


def _as_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".json":
        value: Any = json.loads(path.read_text(encoding="utf-8"))
        records = value if isinstance(value, list) else value.get("data", value)
        return pd.json_normalize(records if isinstance(records, list) else [records])
    raise ValueError(f"Validation supports CSV and JSON files, not {path.suffix}")


def validate_file(path: Path, required_columns: list[str] | None = None) -> list[str]:
    """Return validation errors; an empty list means the file is valid."""
    if not path.exists():
        return ["file does not exist"]
    if path.stat().st_size == 0:
        return ["file is empty"]
    try:
        frame = _as_frame(path)
    except (ValueError, json.JSONDecodeError, pd.errors.ParserError) as exc:
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
    return {
        str(path): validate_file(path, config.required_columns.get(path.stem, []))
        for path in paths
        if path.is_file() and path.name != config.metadata_file.name
    }


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    results = validate_raw_data()
    print(json.dumps(results, indent=2))
    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())