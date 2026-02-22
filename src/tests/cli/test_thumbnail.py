from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

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
def seeded_db_with_thumbnail(tmp_path: Path) -> tuple[Path, Path]:
    """Create a DB and library with an actual thumbnail image."""
    db_path = tmp_path / "test.db"
    library_path = tmp_path / "library"

    # Create library directories
    videos_dir = library_path / "videos"
    thumbnails_dir = library_path / "thumbnails"
    videos_dir.mkdir(parents=True)
    thumbnails_dir.mkdir(parents=True)

    # Create actual thumbnail image (360x240 PNG)
    thumb_file = thumbnails_dir / "Test_Video.png"
    img = Image.new("RGB", (360, 240), color="blue")
    img.save(thumb_file, "PNG")

    # Create a dummy video file
    video_file = videos_dir / "Test_Video.webm"
    video_file.write_text("fake video content")

    # Set up database with relative paths
    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Test Video", "videos/Test_Video.webm", "thumbnails/Test_Video.png")

    return db_path, library_path


def test_thumbnail_by_id_success(runner, seeded_db_with_thumbnail):
    db_path, library_path = seeded_db_with_thumbnail
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "1"
    ])
    assert r.exit_code == 0
    assert "Thumbnail:" in r.stdout
    # Full path is displayed (may be word-wrapped), check for key components
    assert "library/thumbnails/Test_Video.png" in r.stdout
    assert "Resolution: 360x240" in r.stdout
    assert "Format: png" in r.stdout
    assert "Size:" in r.stdout


def test_thumbnail_by_title_success(runner, seeded_db_with_thumbnail):
    db_path, library_path = seeded_db_with_thumbnail
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "Test Video"
    ])
    assert r.exit_code == 0
    assert "Thumbnail:" in r.stdout
    assert "library/thumbnails/Test_Video.png" in r.stdout
    assert "Resolution: 360x240" in r.stdout


def test_thumbnail_not_found_by_id_exits_1(runner, seeded_db_with_thumbnail):
    db_path, library_path = seeded_db_with_thumbnail
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "999"
    ])
    assert r.exit_code == 1
    assert "not found" in r.stdout.lower()


def test_thumbnail_not_found_by_title_exits_1(runner, seeded_db_with_thumbnail):
    db_path, library_path = seeded_db_with_thumbnail
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "Nonexistent Title"
    ])
    assert r.exit_code == 1
    assert "not found" in r.stdout.lower()


def test_thumbnail_ambiguous_title_exits_1(runner, tmp_path, seeded_db_with_duplicates):
    # Create a minimal library directory
    library_path = tmp_path / "library"
    (library_path / "videos").mkdir(parents=True)
    (library_path / "thumbnails").mkdir(parents=True)

    r = runner.invoke(app, [
        "--db", str(seeded_db_with_duplicates),
        "--library", str(library_path),
        "thumbnail", "Duplicate Title"
    ])
    assert r.exit_code == 1
    assert "Multiple videos found" in r.stdout


def test_thumbnail_ambiguous_title_shows_matches(runner, tmp_path, seeded_db_with_duplicates):
    # Create a minimal library directory
    library_path = tmp_path / "library"
    (library_path / "videos").mkdir(parents=True)
    (library_path / "thumbnails").mkdir(parents=True)

    r = runner.invoke(app, [
        "--db", str(seeded_db_with_duplicates),
        "--library", str(library_path),
        "thumbnail", "Duplicate Title"
    ])
    assert r.exit_code == 1
    # Should show matching entries in a table
    assert "Duplicate Title" in r.stdout
    assert "Use the video ID" in r.stdout


def test_thumbnail_missing_file_exits_2(runner, tmp_path):
    """thumbnail should exit 2 if the thumbnail file doesn't exist on disk."""
    db_path = tmp_path / "test.db"
    library_path = tmp_path / "library"

    # Create library directories but no thumbnail file
    (library_path / "videos").mkdir(parents=True)
    (library_path / "thumbnails").mkdir(parents=True)

    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Ghost Video", "videos/ghost.webm", "thumbnails/ghost.png")

    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "1"
    ])
    assert r.exit_code == 2
    assert "not found" in r.stdout.lower()


@patch("crsm.cli.commands.thumbnail.subprocess.Popen")
def test_thumbnail_view_launches_viewer(mock_popen, runner, seeded_db_with_thumbnail):
    db_path, library_path = seeded_db_with_thumbnail
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "1", "--view"
    ])
    assert r.exit_code == 0
    assert "Thumbnail:" in r.stdout
    assert "Test_Video.png" in r.stdout
    mock_popen.assert_called_once()


def test_thumbnail_displays_jpeg_format(runner, tmp_path):
    """Test that JPEG format is correctly identified."""
    db_path = tmp_path / "test.db"
    library_path = tmp_path / "library"

    # Create library directories
    videos_dir = library_path / "videos"
    thumbnails_dir = library_path / "thumbnails"
    videos_dir.mkdir(parents=True)
    thumbnails_dir.mkdir(parents=True)

    # Create JPEG thumbnail
    thumb_file = thumbnails_dir / "Test_Video.jpg"
    img = Image.new("RGB", (640, 480), color="red")
    img.save(thumb_file, "JPEG")

    # Create dummy video
    video_file = videos_dir / "Test_Video.webm"
    video_file.write_text("fake video")

    ensure_schema(db_path)
    repo = CrsmRepo(db_path)
    repo.add_video("Test Video", "videos/Test_Video.webm", "thumbnails/Test_Video.jpg")

    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "1"
    ])
    assert r.exit_code == 0
    assert "Format: jpeg" in r.stdout
    assert "Resolution: 640x480" in r.stdout


def test_thumbnail_size_formatting_kb(runner, seeded_db_with_thumbnail):
    """Test that file size is formatted correctly."""
    db_path, library_path = seeded_db_with_thumbnail
    r = runner.invoke(app, [
        "--db", str(db_path),
        "--library", str(library_path),
        "thumbnail", "1"
    ])
    assert r.exit_code == 0
    # Size should be in KB or B format
    assert "Size:" in r.stdout
    # The test image is small, so it should be in B or KB
    assert " KB" in r.stdout or " B" in r.stdout
