"""Shared fixtures for the ingestion and pipeline tests."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cricsheet"


@pytest.fixture
def cricsheet_fixtures() -> list[Path]:
    """Every committed Cricsheet match fixture."""
    return sorted(FIXTURE_DIR.glob("*.json"))


@pytest.fixture
def cricsheet_archive(cricsheet_fixtures: list[Path]) -> bytes:
    """A Cricsheet-shaped ZIP: one JSON per match plus a non-JSON notes file."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("README.txt", "Cricsheet archive notes\n")
        for fixture in cricsheet_fixtures:
            archive.writestr(fixture.name, fixture.read_text(encoding="utf-8"))
    return buffer.getvalue()


@pytest.fixture
def match_payload() -> dict:
    return json.loads((FIXTURE_DIR / "match_win_by_runs.json").read_text(encoding="utf-8"))


class FakeSession:
    """Minimal stand-in for requests.Session that returns fixed bytes."""

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
