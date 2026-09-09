"""Configuration for the local IPL ingestion layer."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class IngestionConfig:
    raw_dir: Path
    processed_dir: Path
    metadata_file: Path
    source_urls: dict[str, str]
    required_columns: dict[str, list[str]] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_attempts: int = 3


def _json_mapping(name: str, default: dict) -> dict:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must contain valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must contain a JSON object")
    return parsed


def get_config() -> IngestionConfig:
    """Load ingestion settings from environment variables and project defaults."""
    data_dir = Path(os.getenv("IPL_DATA_DIR", PROJECT_ROOT / "data"))
    raw_dir = Path(os.getenv("IPL_RAW_DIR", data_dir / "raw"))
    processed_dir = Path(os.getenv("IPL_PROCESSED_DIR", data_dir / "processed"))
    metadata_file = Path(os.getenv("IPL_METADATA_FILE", raw_dir / "ingestion_metadata.json"))
    return IngestionConfig(
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        metadata_file=metadata_file,
        source_urls=_json_mapping("IPL_SOURCE_URLS", {}),
        required_columns=_json_mapping("IPL_REQUIRED_COLUMNS", {}),
        timeout_seconds=int(os.getenv("IPL_REQUEST_TIMEOUT", "30")),
        retry_attempts=int(os.getenv("IPL_RETRY_ATTEMPTS", "3")),
    )