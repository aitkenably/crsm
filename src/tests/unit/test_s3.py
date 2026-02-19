from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Skip tests if boto3/botocore not installed
pytest.importorskip("boto3")
pytest.importorskip("botocore")

from botocore.exceptions import ClientError

from crsm.s3 import (
    compute_md5,
    needs_upload,
    sync_file,
    S3Publisher,
    SyncResult,
    S3NotAvailableError,
    S3CredentialsError,
    S3UploadError,
)


def test_compute_md5(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    result = compute_md5(test_file)

    # Verify against known MD5 of "hello world"
    expected = hashlib.md5(b"hello world").hexdigest()
    assert result == expected


def test_compute_md5_large_file(tmp_path):
    # Test chunked reading with larger file
    test_file = tmp_path / "large.bin"
    content = b"x" * 10000
    test_file.write_bytes(content)

    result = compute_md5(test_file)

    expected = hashlib.md5(content).hexdigest()
    assert result == expected


def test_needs_upload_file_not_exists():
    mock_client = Mock()

    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_client.head_object.side_effect = ClientError(error_response, "HeadObject")

    result = needs_upload(mock_client, "bucket", "key", Path("/fake/path"))
    assert result is True


def test_needs_upload_file_unchanged(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    local_md5 = compute_md5(test_file)

    mock_client = Mock()
    mock_client.head_object.return_value = {"ETag": f'"{local_md5}"'}

    result = needs_upload(mock_client, "bucket", "key", test_file)
    assert result is False


def test_needs_upload_file_changed(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("new content")

    mock_client = Mock()
    mock_client.head_object.return_value = {"ETag": '"different_md5_hash"'}

    result = needs_upload(mock_client, "bucket", "key", test_file)
    assert result is True


def test_sync_file_skips_unchanged(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    local_md5 = compute_md5(test_file)

    mock_client = Mock()
    mock_client.head_object.return_value = {"ETag": f'"{local_md5}"'}

    result = sync_file(mock_client, "bucket", "key", test_file)

    assert result is False
    mock_client.upload_file.assert_not_called()


def test_sync_file_uploads_new_file(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    mock_client = Mock()
    # Simulate 404 - file doesn't exist
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_client.head_object.side_effect = ClientError(error_response, "HeadObject")

    result = sync_file(mock_client, "bucket", "key", test_file)

    assert result is True
    mock_client.upload_file.assert_called_once_with(str(test_file), "bucket", "key")


def test_sync_file_dry_run(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    mock_client = Mock()
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_client.head_object.side_effect = ClientError(error_response, "HeadObject")

    result = sync_file(mock_client, "bucket", "key", test_file, dry_run=True)

    assert result is True
    mock_client.upload_file.assert_not_called()


def test_sync_file_upload_error(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    mock_client = Mock()
    # File doesn't exist remotely
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_client.head_object.side_effect = ClientError(error_response, "HeadObject")

    # Upload fails
    upload_error = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_client.upload_file.side_effect = ClientError(upload_error, "PutObject")

    with pytest.raises(S3UploadError):
        sync_file(mock_client, "bucket", "key", test_file)


def test_s3_publisher_build_key_with_prefix():
    mock_client = Mock()
    publisher = S3Publisher(mock_client, "bucket", "media")

    key = publisher._build_key("videos", "test.webm")
    assert key == "media/videos/test.webm"


def test_s3_publisher_build_key_without_prefix():
    mock_client = Mock()
    publisher = S3Publisher(mock_client, "bucket", None)

    key = publisher._build_key("videos", "test.webm")
    assert key == "videos/test.webm"


def test_s3_publisher_sync_library(tmp_path):
    # Set up mock client
    mock_client = Mock()
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_client.head_object.side_effect = ClientError(error_response, "HeadObject")

    # Create test files
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()
    thumbnails_dir = tmp_path / "thumbnails"
    thumbnails_dir.mkdir()

    video_file = videos_dir / "test.webm"
    video_file.write_text("video content")
    thumbnail_file = thumbnails_dir / "test.png"
    thumbnail_file.write_text("thumbnail content")

    videos = [
        {
            "id": 1,
            "title": "Test",
            "video_path": str(video_file),
            "thumbnail_path": str(thumbnail_file),
        }
    ]

    publisher = S3Publisher(mock_client, "bucket", "media")
    result = publisher.sync_library(tmp_path, videos, dry_run=True)

    assert result.uploaded == 2  # Video + thumbnail
    assert result.skipped == 0
    assert len(result.errors) == 0


def test_sync_result_defaults():
    result = SyncResult()
    assert result.uploaded == 0
    assert result.skipped == 0
    assert result.errors == []


def test_sync_result_with_values():
    result = SyncResult(uploaded=5, skipped=3, errors=["error1"])
    assert result.uploaded == 5
    assert result.skipped == 3
    assert result.errors == ["error1"]
