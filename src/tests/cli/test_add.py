from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crsm.cli.app import app
from crsm.db import ensure_schema
from crsm.repo import CrsmRepo


@pytest.fixture()
def library_path(tmp_path: Path) -> Path:
    """Create an empty library directory structure."""
    lib_path = tmp_path / "library"
    (lib_path / "videos").mkdir(parents=True)
    (lib_path / "thumbnails").mkdir(parents=True)
    return lib_path


@pytest.fixture()
def source_video(tmp_path: Path) -> Path:
    """Create a fake video file to add."""
    video = tmp_path / "test_video.webm"
    video.write_text("fake video content")
    return video


def test_add_file_not_found_exits_1(runner, temp_db_path, library_path):
    r = runner.invoke(app, [
        "--db", str(temp_db_path),
        "--library", str(library_path),
        "add", "/nonexistent/video.webm"
    ])
    assert r.exit_code == 1
    assert "File not found" in r.stdout


def test_add_unsupported_extension_exits_1(runner, temp_db_path, library_path, tmp_path):
    # Create a non-video file
    txt_file = tmp_path / "file.txt"
    txt_file.write_text("not a video")

    r = runner.invoke(app, [
        "--db", str(temp_db_path),
        "--library", str(library_path),
        "add", str(txt_file)
    ])
    assert r.exit_code == 1
    assert "Unsupported file type" in r.stdout


def test_add_with_copy_default(runner, temp_db_path, library_path, source_video):
    """Test that --copy is the default behavior."""
    # Mock ffmpeg to succeed
    with patch("crsm.library.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        # Create thumbnail file since ffmpeg is mocked
        thumb_path = library_path / "thumbnails" / "test_video.png"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_text("fake thumbnail")

        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(source_video)
        ])

    assert r.exit_code == 0
    assert "Added:" in r.stdout
    assert "videos/test_video.webm" in r.stdout

    # Source should still exist (copy is default)
    assert source_video.exists()

    # Destination should exist
    dest = library_path / "videos" / "test_video.webm"
    assert dest.exists()

    # DB entry should exist with relative paths
    repo = CrsmRepo(temp_db_path)
    video = repo.get_video_by_path("videos/test_video.webm")
    assert video is not None
    assert video["title"] == "test video"
    assert video["video_path"] == "videos/test_video.webm"
    assert video["thumbnail_path"] == "thumbnails/test_video.png"


def test_add_with_move_flag(runner, temp_db_path, library_path, source_video):
    """Test that --move deletes the source file."""
    with patch("crsm.library.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        thumb_path = library_path / "thumbnails" / "test_video.png"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_text("fake thumbnail")

        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(source_video), "--move"
        ])

    assert r.exit_code == 0

    # Source should be deleted (moved)
    assert not source_video.exists()

    # Destination should exist
    dest = library_path / "videos" / "test_video.webm"
    assert dest.exists()


def test_add_with_custom_title(runner, temp_db_path, library_path, source_video):
    """Test --title option."""
    with patch("crsm.library.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        thumb_path = library_path / "thumbnails" / "test_video.png"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_text("fake thumbnail")

        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(source_video),
            "--title", "My Custom Title"
        ])

    assert r.exit_code == 0
    assert '"My Custom Title"' in r.stdout

    repo = CrsmRepo(temp_db_path)
    video = repo.get_video_by_path("videos/test_video.webm")
    assert video["title"] == "My Custom Title"


def test_add_duplicate_without_force_exits_1(runner, temp_db_path, library_path, tmp_path):
    """Test that adding a duplicate without --force fails."""
    # First, add a video
    video1 = tmp_path / "original_video.webm"
    video1.write_text("original content")

    with patch("crsm.library.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        thumb_path = library_path / "thumbnails" / "original_video.png"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_text("fake thumbnail")

        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(video1)
        ])
    assert r.exit_code == 0

    # Now try to add another video with the same filename
    video2 = tmp_path / "original_video.webm"
    video2.write_text("new content")

    r = runner.invoke(app, [
        "--db", str(temp_db_path),
        "--library", str(library_path),
        "add", str(video2)
    ])

    assert r.exit_code == 1
    assert "already exists" in r.stdout
    assert "--force" in r.stdout


def test_add_duplicate_with_force_succeeds(runner, temp_db_path, library_path, tmp_path):
    """Test that --force overwrites existing entry."""
    thumb_path = library_path / "thumbnails" / "my_video.png"

    def create_thumbnail(*args, **kwargs):
        """Side effect that creates the thumbnail file."""
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_text("fake thumbnail")
        from unittest.mock import MagicMock
        result = MagicMock()
        result.returncode = 0
        return result

    # First, add a video
    video1 = tmp_path / "my_video.webm"
    video1.write_text("original content")

    with patch("crsm.library.subprocess.run", side_effect=create_thumbnail):
        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(video1), "--title", "Original Title"
        ])
    assert r.exit_code == 0

    # Verify entry exists
    repo = CrsmRepo(temp_db_path)
    original = repo.get_video_by_path("videos/my_video.webm")
    assert original is not None
    original_id = original["id"]

    # Now add with --force (recreate the source file since it was moved)
    video2 = tmp_path / "my_video.webm"
    video2.write_text("new content")

    with patch("crsm.library.subprocess.run", side_effect=create_thumbnail):
        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(video2), "--title", "New Title", "--force"
        ])

    assert r.exit_code == 0
    assert '"New Title"' in r.stdout

    # Original entry should be gone
    assert repo.get_video_by_id(original_id) is None

    # New entry should exist
    new_video = repo.get_video_by_path("videos/my_video.webm")
    assert new_video is not None
    assert new_video["title"] == "New Title"


def test_thumbnail_failure_rolls_back_video(runner, temp_db_path, library_path, source_video):
    """Test that failed thumbnail generation rolls back the video import."""
    from crsm.library import ThumbnailGenerationError

    with patch("crsm.library.subprocess.run") as mock_run:
        # Make ffmpeg fail
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "ffmpeg error"

        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(source_video)
        ])

    assert r.exit_code == 2
    assert "Thumbnail generation failed" in r.stdout

    # Video should have been rolled back (deleted)
    video_path = library_path / "videos" / "test_video.webm"
    assert not video_path.exists()

    # No DB entry should exist
    repo = CrsmRepo(temp_db_path)
    assert repo.get_video_by_path("videos/test_video.webm") is None


def test_add_derives_title_from_filename(runner, temp_db_path, library_path, tmp_path):
    """Test that title is derived from filename with underscores replaced."""
    video = tmp_path / "my_cool_video_2024.webm"
    video.write_text("content")

    with patch("crsm.library.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        thumb_path = library_path / "thumbnails" / "my_cool_video_2024.png"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_text("fake thumbnail")

        r = runner.invoke(app, [
            "--db", str(temp_db_path),
            "--library", str(library_path),
            "add", str(video)
        ])

    assert r.exit_code == 0

    repo = CrsmRepo(temp_db_path)
    video = repo.get_video_by_path("videos/my_cool_video_2024.webm")
    assert video["title"] == "my cool video 2024"
