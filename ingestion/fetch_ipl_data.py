"""Download configured IPL datasets into the immutable raw data zone."""

from __future__ import annotations

import argparse
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.config import IngestionConfig, file_sha256, get_config


LOGGER = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		return json.dumps({
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"level": record.levelname,
			"message": record.getMessage(),
		})


def configure_logging() -> None:
	handler = logging.StreamHandler()
	handler.setFormatter(JsonFormatter())
	logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def _session(retry_attempts: int) -> requests.Session:
	retry = Retry(
		total=retry_attempts,
		backoff_factor=1,
		status_forcelist=(429, 500, 502, 503, 504),
		allowed_methods=frozenset({"GET"}),
		raise_on_status=False,
	)
	session = requests.Session()
	session.mount("http://", HTTPAdapter(max_retries=retry))
	session.mount("https://", HTTPAdapter(max_retries=retry))
	return session


def _record_count(path: Path, suffix: str | None = None) -> int:
	# `suffix` lets callers count a staging file that is still named *.part while
	# dispatching on the format the file will actually have once it is swapped in.
	suffix = (suffix or path.suffix).lower()
	if suffix == ".zip":
		# Count only the JSON members, because those are the records the Snowflake
		# loader actually inserts; archives also ship notes such as README.txt.
		with zipfile.ZipFile(path) as archive:
			return sum(
				1
				for name in archive.namelist()
				if not name.endswith("/") and name.lower().endswith(".json")
			)
	if suffix == ".csv":
		return int(pd.read_csv(path).shape[0])
	if suffix == ".json":
		value: Any = json.loads(path.read_text(encoding="utf-8"))
		if isinstance(value, list):
			return len(value)
		if isinstance(value, dict):
			for key in ("data", "records", "matches", "deliveries", "players", "teams"):
				if isinstance(value.get(key), list):
					return len(value[key])
			return 1
	raise ValueError(f"Cannot determine record count for {path.name}")


def _filename(dataset: str, url: str) -> str:
	name = Path(url.split("?", 1)[0]).name or f"{dataset}.bin"
	return name if Path(name).stem == dataset else f"{dataset}_{name}"


def fetch_dataset(
	dataset: str,
	url: str,
	config: IngestionConfig,
	session: requests.Session | None = None,
) -> dict[str, Any]:
	"""Fetch one configured dataset and return its metadata record."""
	config.raw_dir.mkdir(parents=True, exist_ok=True)
	output_path = config.raw_dir / _filename(dataset, url)
	client = session or _session(config.retry_attempts)
	LOGGER.info("Fetching dataset=%s source=%s", dataset, url)
	response = client.get(url, timeout=config.timeout_seconds)
	response.raise_for_status()
	# Write to a temporary file and swap it in, so an interrupted or retried
	# download never leaves a truncated file in the raw zone.
	staging_path = output_path.with_name(output_path.name + ".part")
	try:
		staging_path.write_bytes(response.content)
		record_count = _record_count(staging_path, output_path.suffix)
		os.replace(staging_path, output_path)
	finally:
		staging_path.unlink(missing_ok=True)
	metadata = {
		"dataset": dataset,
		"source": url,
		"ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
		"file_name": output_path.name,
		"file_hash": file_sha256(output_path),
		"record_count": record_count,
	}
	LOGGER.info("Stored dataset=%s file=%s records=%s", dataset, output_path, metadata["record_count"])
	return metadata


def ingest(config: IngestionConfig | None = None) -> list[dict[str, Any]]:
	"""Fetch every configured source and write metadata for this run."""
	config = config or get_config()
	if not config.source_urls:
		raise ValueError("No IPL sources configured; set IPL_SOURCE_URLS to a JSON object")
	metadata = [fetch_dataset(dataset, url, config) for dataset, url in config.source_urls.items()]
	config.metadata_file.parent.mkdir(parents=True, exist_ok=True)
	config.metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
	return metadata


def main() -> None:
	argparse.ArgumentParser(description=__doc__).parse_args()
	configure_logging()
	ingest()


if __name__ == "__main__":
	main()
