from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crsm.cli.app import app
from crsm.db import ensure_schema
from crsm.repo import CrsmRepo


def test_live_no_videos(runner, temp_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    r = runner.invoke(
        app,
        [
            "--db", str(temp_db_path),
            "--library", str(library_dir),
            "live",
            "--no-sync",
            "--public-base-url", "https://example.com",
        ],
    )
    assert r.exit_code == 0
    assert "No videos found" in r.stdout


def test_live_requires_public_base_url_for_catalog(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    # Create empty config to avoid loading user's real config
    config_file = tmp_path / "config.toml"
    config_file.write_text("")

    r = runner.invoke(
        app,
        [
            "--config", str(config_file),
            "--db", str(seeded_db_path),
            "--library", str(library_dir),
            "live",
            "--no-sync",
        ],
    )

    assert r.exit_code == 1
    assert "Public base URL is required" in r.stdout


def test_live_requires_bucket_for_sync(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    # Create empty config to avoid loading user's real config
    config_file = tmp_path / "config.toml"
    config_file.write_text("")

    r = runner.invoke(
        app,
        [
            "--config", str(config_file),
            "--db", str(seeded_db_path),
            "--library", str(library_dir),
            "live",
            "--no-catalog",
        ],
    )
    assert r.exit_code == 1
    assert "S3 bucket is required" in r.stdout


def test_live_catalog_only(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    r = runner.invoke(
        app,
        [
            "--db", str(seeded_db_path),
            "--library", str(library_dir),
            "live",
            "--no-sync",
            "--public-base-url", "https://cdn.example.com",
        ],
    )
    assert r.exit_code == 0
    assert "Generated catalog" in r.stdout

    catalog_path = library_dir / "catalog.json"
    assert catalog_path.exists()

    catalog_data = json.loads(catalog_path.read_text())
    assert "videos" in catalog_data
    assert len(catalog_data["videos"]) == 4  # seeded_db_path has 4 videos


def test_live_catalog_with_prefix(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    r = runner.invoke(
        app,
        [
            "--db", str(seeded_db_path),
            "--library", str(library_dir),
            "live",
            "--no-sync",
            "--public-base-url", "https://cdn.example.com",
            "--prefix", "media",
        ],
    )
    assert r.exit_code == 0

    catalog_path = library_dir / "catalog.json"
    catalog_data = json.loads(catalog_path.read_text())

    # Check that URLs include the prefix
    first_video = catalog_data["videos"][0]
    assert "/media/videos/" in first_video["video_url"]
    assert "/media/thumbnails/" in first_video["thumbnail_url"]


def test_live_catalog_sorted_by_title(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    r = runner.invoke(
        app,
        [
            "--db", str(seeded_db_path),
            "--library", str(library_dir),
            "live",
            "--no-sync",
            "--public-base-url", "https://cdn.example.com",
        ],
    )
    assert r.exit_code == 0

    catalog_path = library_dir / "catalog.json"
    catalog_data = json.loads(catalog_path.read_text())

    # Videos should be sorted by title
    titles = [v["title"] for v in catalog_data["videos"]]
    assert titles == sorted(titles, key=str.lower)


# S3 sync tests require boto3
boto3 = pytest.importorskip("boto3")


def test_live_no_catalog_flag(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    # Mock the S3 client to avoid actual AWS calls
    with patch("crsm.s3.get_s3_client") as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock S3Publisher
        with patch("crsm.s3.S3Publisher") as mock_publisher_cls:
            mock_publisher = Mock()
            mock_publisher.sync_library.return_value = Mock(uploaded=0, skipped=0, errors=[])
            mock_publisher_cls.return_value = mock_publisher

            r = runner.invoke(
                app,
                [
                    "--db", str(seeded_db_path),
                    "--library", str(library_dir),
                    "live",
                    "--no-catalog",
                    "--bucket", "test-bucket",
                    "--dry-run",
                ],
            )

    # Catalog should not be generated
    catalog_path = library_dir / "catalog.json"
    assert not catalog_path.exists()


def test_live_dry_run_shows_message(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    # Mock the S3 client
    with patch("crsm.s3.get_s3_client") as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with patch("crsm.s3.S3Publisher") as mock_publisher_cls:
            mock_publisher = Mock()
            mock_publisher.sync_library.return_value = Mock(uploaded=2, skipped=0, errors=[])
            mock_publisher_cls.return_value = mock_publisher

            r = runner.invoke(
                app,
                [
                    "--db", str(seeded_db_path),
                    "--library", str(library_dir),
                    "live",
                    "--bucket", "test-bucket",
                    "--public-base-url", "https://example.com",
                    "--dry-run",
                ],
            )

    assert r.exit_code == 0
    assert "Dry run" in r.stdout


def test_live_s3_credentials_error(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    from crsm.s3 import S3CredentialsError

    with patch("crsm.s3.get_s3_client") as mock_get_client:
        mock_get_client.side_effect = S3CredentialsError("AWS credentials not found")

        r = runner.invoke(
            app,
            [
                "--db", str(seeded_db_path),
                "--library", str(library_dir),
                "live",
                "--bucket", "test-bucket",
                "--public-base-url", "https://example.com",
            ],
        )

    assert r.exit_code == 1
    assert "credentials" in r.stdout.lower()


def test_live_sync_errors_exit_code_2(runner, seeded_db_path, tmp_path):
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    with patch("crsm.s3.get_s3_client") as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with patch("crsm.s3.S3Publisher") as mock_publisher_cls:
            mock_publisher = Mock()
            mock_publisher.sync_library.return_value = Mock(
                uploaded=1,
                skipped=0,
                errors=["Failed to upload video.webm"],
            )
            mock_publisher_cls.return_value = mock_publisher

            r = runner.invoke(
                app,
                [
                    "--db", str(seeded_db_path),
                    "--library", str(library_dir),
                    "live",
                    "--bucket", "test-bucket",
                    "--public-base-url", "https://example.com",
                ],
            )

    assert r.exit_code == 2
    assert "Errors" in r.stdout
