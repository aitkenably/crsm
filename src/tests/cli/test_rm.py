from __future__ import annotations

from pathlib import Path

import pytest

from crsm.cli.app import app
from crsm.repo import CrsmRepo
from crsm.db import ensure_schema


@pytest.fixture()
def seeded_db_with_duplicates(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Unique Title")
    repo.add_video("Duplicate Title")
    repo.add_video("Duplicate Title")
    return db_path


def test_rm_by_id_success(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "1", "--yes"])
    assert r.exit_code == 0
    assert 'Removed: "Chill Beats"' in r.stdout

    # Verify removal
    repo = CrsmRepo(seeded_db_path)
    assert repo.get_video_by_id(1) is None


def test_rm_by_title_success(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "Chill Beats", "--yes"])
    assert r.exit_code == 0
    assert 'Removed: "Chill Beats"' in r.stdout

    # Verify removal
    repo = CrsmRepo(seeded_db_path)
    videos = repo.get_videos_by_title("Chill Beats")
    assert len(videos) == 0


def test_rm_not_found_by_id_exits_1(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "999", "--yes"])
    assert r.exit_code == 1
    assert "not found" in r.stdout.lower()


def test_rm_not_found_by_title_exits_1(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "Nonexistent Title", "--yes"])
    assert r.exit_code == 1
    assert "not found" in r.stdout.lower()


def test_rm_ambiguous_title_exits_1(runner, seeded_db_with_duplicates):
    r = runner.invoke(app, ["--db", str(seeded_db_with_duplicates), "rm", "Duplicate Title", "--yes"])
    assert r.exit_code == 1
    assert "Multiple videos found" in r.stdout


def test_rm_ambiguous_title_shows_matches(runner, seeded_db_with_duplicates):
    r = runner.invoke(app, ["--db", str(seeded_db_with_duplicates), "rm", "Duplicate Title", "--yes"])
    assert r.exit_code == 1
    # Should show matching entries in a table
    assert "Duplicate Title" in r.stdout
    assert "Use the video ID" in r.stdout


def test_rm_with_yes_skips_prompt(runner, seeded_db_path):
    # With --yes, should not prompt and should succeed
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "1", "--yes"])
    assert r.exit_code == 0
    assert 'Removed: "Chill Beats"' in r.stdout


def test_rm_confirmation_declined(runner, seeded_db_path):
    # Simulate user typing 'n' to decline
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "1"], input="n\n")
    assert r.exit_code == 0
    assert "Cancelled" in r.stdout

    # Verify NOT removed
    repo = CrsmRepo(seeded_db_path)
    assert repo.get_video_by_id(1) is not None


def test_rm_confirmation_accepted(runner, seeded_db_path):
    # Simulate user typing 'y' to confirm
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "1"], input="y\n")
    assert r.exit_code == 0
    assert 'Removed: "Chill Beats"' in r.stdout

    # Verify removed
    repo = CrsmRepo(seeded_db_path)
    assert repo.get_video_by_id(1) is None


def test_rm_with_keep_files(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "rm", "1", "--yes", "--keep-files"])
    assert r.exit_code == 0
    assert 'Removed: "Chill Beats"' in r.stdout

    # Verify DB removal
    repo = CrsmRepo(seeded_db_path)
    assert repo.get_video_by_id(1) is None
