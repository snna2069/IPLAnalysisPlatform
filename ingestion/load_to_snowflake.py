"""Load validated local IPL files into Snowflake raw tables."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ingestion.config import get_config


LOGGER = logging.getLogger(__name__)
DATASET_TABLES = {
    "matches": "RAW_MATCHES",
    "deliveries": "RAW_DELIVERIES",
    "players": "RAW_PLAYERS",
    "teams": "RAW_TEAMS",
}


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: str | None = None


def get_snowflake_config() -> SnowflakeConfig:
    required = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "IPL_ANALYTICS"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "RAW"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Snowflake environment variables: {', '.join(missing)}")
    return SnowflakeConfig(**required, role=os.getenv("SNOWFLAKE_ROLE"))


def _connect(config: SnowflakeConfig):
    try:
        import snowflake.connector
    except ImportError as exc:
        raise RuntimeError("Install snowflake-connector-python to load Snowflake data") from exc
    options = vars(config).copy()
    options = {key: value for key, value in options.items() if value is not None}
    return snowflake.connector.connect(**options)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _records(path: Path) -> Iterator[tuple[str, Any]]:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith("/") or not name.lower().endswith(".json"):
                    continue
                yield name, json.loads(archive.read(name).decode("utf-8"))
        return
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            yield from ((str(index), record) for index, record in enumerate(value))
        else:
            yield "0", value
        return
    if path.suffix.lower() == ".csv":
        import pandas as pd

        frame = pd.read_csv(path)
        yield from ((str(index), record) for index, record in enumerate(frame.to_dict(orient="records")))
        return
    raise ValueError(f"Unsupported Snowflake input format: {path.suffix}")


def _dataset_name(path: Path) -> str:
    stem = path.stem.lower()
    for dataset in DATASET_TABLES:
        if stem == dataset or stem.startswith(f"{dataset}_"):
            return dataset
    raise ValueError(f"Cannot map {path.name} to an IPL dataset table")


def load_to_snowflake() -> dict[str, int]:
    """Load each unrecorded validated raw file once and return row counts."""
    config = get_config()
    snowflake_config = get_snowflake_config()
    connection = _connect(snowflake_config)
    counts: dict[str, int] = {}
    try:
        cursor = connection.cursor()
        try:
            for path in sorted(config.raw_dir.iterdir()):
                if not path.is_file() or path.name == config.metadata_file.name:
                    continue
                dataset = _dataset_name(path)
                table = DATASET_TABLES[dataset]
                file_hash = _file_hash(path)
                cursor.execute(
                    "SELECT 1 FROM INGESTION_METADATA WHERE FILE_HASH = %s LIMIT 1",
                    (file_hash,),
                )
                if cursor.fetchone():
                    LOGGER.info("Skipping already loaded file=%s", path)
                    continue
                row_count = 0
                for record_id, payload in _records(path):
                    cursor.execute(
                        f"INSERT INTO {table} "
                        "(RECORD_ID, SOURCE_FILE, FILE_HASH, RAW_PAYLOAD, LOADED_AT) "
                        "SELECT %s, %s, %s, PARSE_JSON(%s), %s",
                        (record_id, path.name, file_hash, json.dumps(payload), datetime.now(timezone.utc)),
                    )
                    row_count += 1
                cursor.execute(
                    "INSERT INTO INGESTION_METADATA "
                    "(FILE_HASH, DATASET_NAME, SOURCE_FILE, RECORD_COUNT, LOADED_AT, LOAD_STATUS) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (file_hash, dataset, path.name, row_count, datetime.now(timezone.utc), "LOADED"),
                )
                counts[dataset] = counts.get(dataset, 0) + row_count
                LOGGER.info("Loaded dataset=%s records=%d file=%s", dataset, row_count, path.name)
            connection.commit()
        finally:
            cursor.close()
    except Exception:
        connection.rollback()
        LOGGER.exception("Snowflake load failed")
        raise
    finally:
        connection.close()
    return counts