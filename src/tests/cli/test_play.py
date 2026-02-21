from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crsm.cli.app import app
from crsm.repo import CrsmRepo
from crsm.db import ensure_schema


@pytest.fixture()
def seeded_db_with_duplicates(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Unique Title", "videos/Unique_Title.webm", "thumbnails/Unique_Title.png")
    repo.add_video("Duplicate Title", "videos/Duplicate_Title.webm", "thumbnails/Duplicate_Title.png")
    repo.add_video("Duplicate Title", "videos/Duplicate_Title2.webm", "thumbnails/Duplicate_Title2.png")
    return db_path


@pytest.fixture()
def seeded_db_with_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create a DB and library with actual video files."""
    db_path = tmp_path / "test.db"
    library_path = tmp_path / "library"

    # Create library directories
    videos_dir = library_path / "videos"
    thumbnails_dir = library_path / "thumbnails"
    videos_dir.mkdir(parents=True)
    thumbnails_dir.mkdir(parents=True)

    # Create actual files
    video_file = videos_dir / "Test_Video.webm"
    thumb_file = thumbnails_dir / "Test_Video.png"
    video_file.write_text("fake video content")
    thumb_file.write_text("fake thumbnail content")

    # Set up database with relative paths
    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Test Video", "videos/Test_Video.webm", "thumbnails/Test_Video.png")

    return db_path, library_path


@patch("crsm.cli.commands.play.subprocess.Popen")
def test_play_by_id_success(mock_popen, runner, seeded_db_with_files):
    db_path, library_path = seeded_db_with_files
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "play", "1"
    ])
    assert r.exit_code == 0
    assert 'Playing: "Test Video"' in r.stdout
    mock_popen.assert_called_once()


@patch("crsm.cli.commands.play.subprocess.Popen")
def test_play_by_title_success(mock_popen, runner, seeded_db_with_files):
    db_path, library_path = seeded_db_with_files
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "play", "Test Video"
    ])
    assert r.exit_code == 0
    assert 'Playing: "Test Video"' in r.stdout
    mock_popen.assert_called_once()


def test_play_not_found_by_id_exits_1(runner, seeded_db_with_files):
    db_path, library_path = seeded_db_with_files
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "play", "999"
    ])
    assert r.exit_code == 1
    assert "not found" in r.stdout.lower()


def test_play_not_found_by_title_exits_1(runner, seeded_db_with_files):
    db_path, library_path = seeded_db_with_files
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "play", "Nonexistent Title"
    ])
    assert r.exit_code == 1
    assert "not found" in r.stdout.lower()


def test_play_ambiguous_title_exits_1(runner, tmp_path, seeded_db_with_duplicates):
    # Create a minimal library directory
    library_path = tmp_path / "library"
    (library_path / "videos").mkdir(parents=True)
    (library_path / "thumbnails").mkdir(parents=True)

    r = runner.invoke(app, [
        "--db", str(seeded_db_with_duplicates),
        "--library", str(library_path),
        "play", "Duplicate Title"
    ])
    assert r.exit_code == 1
    assert "Multiple videos found" in r.stdout


def test_play_ambiguous_title_shows_matches(runner, tmp_path, seeded_db_with_duplicates):
    # Create a minimal library directory
    library_path = tmp_path / "library"
    (library_path / "videos").mkdir(parents=True)
    (library_path / "thumbnails").mkdir(parents=True)

    r = runner.invoke(app, [
        "--db", str(seeded_db_with_duplicates),
        "--library", str(library_path),
        "play", "Duplicate Title"
    ])
    assert r.exit_code == 1
    # Should show matching entries in a table
    assert "Duplicate Title" in r.stdout
    assert "Use the video ID" in r.stdout


def test_play_missing_file_exits_2(runner, tmp_path):
    """play should exit 2 if the video file doesn't exist on disk."""
    db_path = tmp_path / "test.db"
    library_path = tmp_path / "library"

    # Create library directories but no video file
    (library_path / "videos").mkdir(parents=True)
    (library_path / "thumbnails").mkdir(parents=True)

    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Ghost Video", "videos/ghost.webm", "thumbnails/ghost.png")

    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "play", "1"
    ])
    assert r.exit_code == 2
    assert "not found" in r.stdout.lower()
