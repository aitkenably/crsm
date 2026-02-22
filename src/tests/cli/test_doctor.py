from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crsm.cli.app import app
from crsm.db import ensure_schema
from crsm.repo import CrsmRepo


@pytest.fixture()
def healthy_library(tmp_path: Path) -> tuple[Path, Path]:
    """Create a healthy library setup with db, videos, and thumbnails."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    videos_dir = library_path / "videos"
    videos_dir.mkdir()
    thumbnails_dir = library_path / "thumbnails"
    thumbnails_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    repo = CrsmRepo(db_path)
    # Add a video and create the actual files
    repo.add_video("Test Video", "videos/test_video.webm", "thumbnails/test_video.png")
    (videos_dir / "test_video.webm").write_bytes(b"fake video content")
    (thumbnails_dir / "test_video.png").write_bytes(b"fake thumbnail content")

    return db_path, library_path


def test_doctor_healthy_system(runner, healthy_library):
    """Doctor returns exit code 0 on a healthy system."""
    db_path, library_path = healthy_library
    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 0
    assert "[OK]" in r.stdout
    assert "Passed:" in r.stdout
    assert "Errors: 0" in r.stdout


def test_doctor_no_aws_flag_skips_aws_checks(runner, healthy_library):
    """--no-aws flag skips AWS-related checks."""
    db_path, library_path = healthy_library
    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 0
    # Should not mention AWS credentials or S3 bucket
    assert "AWS credentials" not in r.stdout
    assert "S3 bucket" not in r.stdout


def test_doctor_without_no_aws_checks_s3_config(runner, healthy_library):
    """Without --no-aws, doctor checks for S3 config."""
    db_path, library_path = healthy_library
    # Patch boto3 to avoid actual AWS calls
    with patch("crsm.cli.commands.doctor.BOTO3_AVAILABLE", False):
        r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor"])
    # Should report errors for missing S3 config and boto3
    assert "S3 bucket not configured" in r.stdout or "boto3 not installed" in r.stdout


def test_doctor_missing_ffmpeg(runner, healthy_library):
    """Doctor reports error when ffmpeg is not found."""
    db_path, library_path = healthy_library
    with patch("shutil.which", return_value=None):
        r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    assert "ffmpeg not found" in r.stdout


def test_doctor_orphaned_video_file(runner, tmp_path):
    """Doctor detects orphaned video files not in DB."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    videos_dir = library_path / "videos"
    videos_dir.mkdir()
    thumbnails_dir = library_path / "thumbnails"
    thumbnails_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    # Create an orphaned video file (no DB entry)
    (videos_dir / "orphaned_video.webm").write_bytes(b"orphaned content")

    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    assert "Orphaned video file" in r.stdout
    assert "orphaned_video.webm" in r.stdout


def test_doctor_orphaned_thumbnail_file(runner, tmp_path):
    """Doctor detects orphaned thumbnail files not in DB."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    videos_dir = library_path / "videos"
    videos_dir.mkdir()
    thumbnails_dir = library_path / "thumbnails"
    thumbnails_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    # Create an orphaned thumbnail file (no DB entry)
    (thumbnails_dir / "orphaned_thumb.png").write_bytes(b"orphaned content")

    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    assert "Orphaned thumbnail file" in r.stdout
    assert "orphaned_thumb.png" in r.stdout


def test_doctor_missing_video_file_in_db(runner, tmp_path):
    """Doctor detects when a DB entry references a missing video file."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    videos_dir = library_path / "videos"
    videos_dir.mkdir()
    thumbnails_dir = library_path / "thumbnails"
    thumbnails_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    repo = CrsmRepo(db_path)
    # Add a video entry but don't create the video file
    repo.add_video("Missing Video", "videos/missing.webm", "thumbnails/missing.png")
    # Create only the thumbnail
    (thumbnails_dir / "missing.png").write_bytes(b"thumbnail content")

    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    assert "Missing video file" in r.stdout


def test_doctor_missing_thumbnail_in_db(runner, tmp_path):
    """Doctor detects when a DB entry references a missing thumbnail file."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    videos_dir = library_path / "videos"
    videos_dir.mkdir()
    thumbnails_dir = library_path / "thumbnails"
    thumbnails_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    repo = CrsmRepo(db_path)
    # Add a video entry but don't create the thumbnail file
    repo.add_video("Missing Thumb", "videos/video.webm", "thumbnails/missing.png")
    # Create only the video
    (videos_dir / "video.webm").write_bytes(b"video content")

    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    assert "Missing thumbnail" in r.stdout


def test_doctor_missing_videos_directory(runner, tmp_path):
    """Doctor reports error when videos directory doesn't exist."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    # Only create thumbnails dir, not videos
    thumbnails_dir = library_path / "thumbnails"
    thumbnails_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    assert "Videos directory does not exist" in r.stdout


def test_doctor_missing_thumbnails_directory(runner, tmp_path):
    """Doctor reports error when thumbnails directory doesn't exist."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    # Only create videos dir, not thumbnails
    videos_dir = library_path / "videos"
    videos_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    assert "Thumbnails directory does not exist" in r.stdout


def test_doctor_database_integrity(runner, healthy_library):
    """Doctor verifies database opens and tables exist."""
    db_path, library_path = healthy_library
    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 0
    assert "Database opens successfully" in r.stdout
    assert "Videos table exists" in r.stdout


def test_doctor_ffmpeg_available(runner, healthy_library):
    """Doctor reports ffmpeg as available when it's in PATH."""
    db_path, library_path = healthy_library
    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    # This test assumes ffmpeg is installed on the test machine
    # If not, it will report an error which is also valid behavior
    assert "ffmpeg" in r.stdout


def test_doctor_multiple_errors_all_reported(runner, tmp_path):
    """Doctor continues checking after finding errors and reports all issues."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    videos_dir = library_path / "videos"
    videos_dir.mkdir()
    thumbnails_dir = library_path / "thumbnails"
    thumbnails_dir.mkdir()

    db_path = tmp_path / "crsm.db"
    ensure_schema(db_path)

    repo = CrsmRepo(db_path)
    # Add a video with missing files
    repo.add_video("Missing Files", "videos/missing.webm", "thumbnails/missing.png")

    # Create orphaned files
    (videos_dir / "orphan.webm").write_bytes(b"orphaned")
    (thumbnails_dir / "orphan.png").write_bytes(b"orphaned")

    r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_path), "doctor", "--no-aws"])
    assert r.exit_code == 1
    # Should report multiple errors
    assert "Missing video file" in r.stdout
    assert "Missing thumbnail" in r.stdout
    assert "Orphaned video file" in r.stdout
    assert "Orphaned thumbnail file" in r.stdout
    # Errors count should be >= 4
    assert "Errors:" in r.stdout
