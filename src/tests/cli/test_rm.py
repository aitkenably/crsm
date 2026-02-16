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
    repo.add_video("Unique Title", "videos/Unique_Title.webm", "thumbnails/Unique_Title.png")
    repo.add_video("Duplicate Title", "videos/Duplicate_Title.webm", "thumbnails/Duplicate_Title.png")
    repo.add_video("Duplicate Title", "videos/Duplicate_Title.webm", "thumbnails/Duplicate_Title.png")
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


@pytest.fixture()
def seeded_db_with_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create a DB and library with actual files."""
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


def test_rm_deletes_files(runner, seeded_db_with_files):
    db_path, library_path = seeded_db_with_files
    video_file = library_path / "videos" / "Test_Video.webm"
    thumb_file = library_path / "thumbnails" / "Test_Video.png"

    # Verify files exist before removal
    assert video_file.exists()
    assert thumb_file.exists()

    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "rm", "1", "--yes"
    ])
    assert r.exit_code == 0
    assert 'Removed: "Test Video"' in r.stdout

    # Verify files are deleted
    assert not video_file.exists()
    assert not thumb_file.exists()


def test_rm_keep_files_preserves_files(runner, seeded_db_with_files):
    db_path, library_path = seeded_db_with_files
    video_file = library_path / "videos" / "Test_Video.webm"
    thumb_file = library_path / "thumbnails" / "Test_Video.png"

    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "rm", "1", "--yes", "--keep-files"
    ])
    assert r.exit_code == 0

    # Verify files still exist
    assert video_file.exists()
    assert thumb_file.exists()


def test_rm_missing_files_still_succeeds(runner, tmp_path):
    """rm should succeed even if files don't exist on disk."""
    db_path = tmp_path / "test.db"
    library_path = tmp_path / "library"

    # Create library directories but no files
    (library_path / "videos").mkdir(parents=True)
    (library_path / "thumbnails").mkdir(parents=True)

    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Ghost Video", "videos/ghost.webm", "thumbnails/ghost.png")

    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "rm", "1", "--yes"
    ])
    # Should succeed - DB entry removed, missing files logged as warning
    assert r.exit_code == 0
    assert 'Removed: "Ghost Video"' in r.stdout
