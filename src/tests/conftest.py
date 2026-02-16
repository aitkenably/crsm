from __future__ import annotations

from pathlib import Path
import pytest
from typer.testing import CliRunner

from crsm.db import ensure_schema
from crsm.repo import CrsmRepo


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture()
def temp_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "crsm_test.db"
    ensure_schema(db_path)
    return db_path

@pytest.fixture()
def seeded_db_path(temp_db_path: Path) -> Path:
    repo = CrsmRepo(temp_db_path)
    repo.add_video("Chill Beats", "videos/Chill_Beats.webm", "thumbnails/Chill_Beats.png")
    repo.add_video("Study Music 2", "videos/Study_Music_2.webm", "thumbnails/Study_Music_2.png")
    repo.add_video("Alpha Waves", "videos/Alpha_Waves.webm", "thumbnails/Alpha_Waves.png")
    repo.add_video("Zen Garden", "videos/Zen_Garden.webm", "thumbnails/Zen_Garden.png")
    return temp_db_path