from __future__ import annotations

from pathlib import Path
import pytest
from typer.testing import CliRunner

from crsm.db import ensure_schema

@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture()
def temp_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "crsm_test.db"
    ensure_schema(db_path)
    return db_path