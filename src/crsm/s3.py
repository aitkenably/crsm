from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class S3NotAvailableError(Exception):
    """Raised when boto3 is not installed."""


class S3CredentialsError(Exception):
    """Raised when AWS credentials are invalid or missing."""


class S3UploadError(Exception):
    """Raised when an S3 upload fails."""


def get_s3_client():
    """
    Create and return an S3 client.

    Raises:
        S3NotAvailableError: If boto3 is not installed
        S3CredentialsError: If AWS credentials are invalid or missing
    """
    if not BOTO3_AVAILABLE:
        raise S3NotAvailableError(
            "boto3 is not installed. Install with: pip install crsm[s3]"
        )

    try:
        client = boto3.client("s3")
        # Validate credentials by making a simple call
        client.list_buckets()
        return client
    except NoCredentialsError:
        raise S3CredentialsError("AWS credentials not found")
    except PartialCredentialsError:
        raise S3CredentialsError("Incomplete AWS credentials")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("InvalidAccessKeyId", "SignatureDoesNotMatch"):
            raise S3CredentialsError(f"Invalid AWS credentials: {e}")
        raise


SHA256_TAG_KEY = "sha256"


def compute_sha256(file_path: Path) -> str:
    """
    Compute SHA256 hash of a file.

    Returns:
        SHA256 hash as a hex string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def needs_upload(client, bucket: str, key: str, local_path: Path) -> bool:
    """
    Check if a file needs to be uploaded by comparing SHA256 hash stored as object tag.

    Args:
        client: boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        local_path: Path to local file

    Returns:
        True if file needs upload, False if remote matches local
    """
    try:
        response = client.get_object_tagging(Bucket=bucket, Key=key)
        tags = {tag["Key"]: tag["Value"] for tag in response.get("TagSet", [])}
        remote_hash = tags.get(SHA256_TAG_KEY)
        if not remote_hash:
            # Object exists but has no sha256 tag - re-upload to add tag
            return True
        local_hash = compute_sha256(local_path)
        return remote_hash != local_hash
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return True
        raise


def sync_file(
    client,
    bucket: str,
    key: str,
    local_path: Path,
    dry_run: bool = False,
) -> bool:
    """
    Upload a file to S3 if it has changed.

    Args:
        client: boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        local_path: Path to local file
        dry_run: If True, don't actually upload

    Returns:
        True if file was uploaded (or would be in dry_run), False if skipped
    """

    if not needs_upload(client, bucket, key, local_path):
        logging.debug(f"Skipping {key} (unchanged)")
        return False

    local_hash = compute_sha256(local_path)

    if dry_run:
        logging.info(f"Would upload {local_path} -> s3://{bucket}/{key}")
        return True

    try:
        client.upload_file(
            str(local_path),
            bucket,
            key,
            ExtraArgs={"Tagging": f"{SHA256_TAG_KEY}={local_hash}"},
        )
        logging.info(f"Uploaded {local_path} -> s3://{bucket}/{key}")
        return True
    except ClientError as e:
        raise S3UploadError(f"Failed to upload {local_path}: {e}")

@dataclass
class SyncResult:
    uploaded: int = 0
    skipped: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class S3Publisher:
    """Handles syncing library files to S3."""

    def __init__(
        self,
        client,
        bucket: str,
        prefix: Optional[str] = None,
    ):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/") if prefix else ""

    def _build_key(self, subdir: str, filename: str) -> str:
        """Build S3 object key from subdir and filename."""
        parts = [self.prefix, subdir, filename] if self.prefix else [subdir, filename]
        return "/".join(parts)

    def sync_library(
        self,
        library_path: Path,
        videos: list,
        catalog_path: Optional[Path] = None,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> SyncResult:
        """
        Sync library files to S3.

        Args:
            library_path: Path to local library directory
            videos: List of video records to sync
            catalog_path: Optional path to catalog.json file
            dry_run: If True, don't actually upload
            progress_callback: Optional callback called after each file with (filename, advance_count)

        Returns:
            SyncResult with counts of uploaded/skipped/errors
        """
        result = SyncResult()

        # Sync videos and thumbnails
        for video in videos:
            video_path = library_path / video["video_path"]
            thumbnail_path = library_path / video["thumbnail_path"]

            # Sync thumbnail file
            thumbnail_key = self._build_key("thumbnails", thumbnail_path.name)
            try:
                if sync_file(self.client, self.bucket, thumbnail_key, thumbnail_path, dry_run):
                    result.uploaded += 1
                else:
                    result.skipped += 1
            except S3UploadError as e:
                result.errors.append(str(e))
            if progress_callback:
                progress_callback(thumbnail_path.name, 1)

            # Sync video file
            video_key = self._build_key("videos", video_path.name)
            try:
                if sync_file(self.client, self.bucket, video_key, video_path, dry_run):
                    result.uploaded += 1
                else:
                    result.skipped += 1
            except S3UploadError as e:
                result.errors.append(str(e))
            if progress_callback:
                progress_callback(video_path.name, 1)

        # Sync catalog if provided
        if catalog_path and catalog_path.exists():
            catalog_key = self._build_key("", "catalog.json") if not self.prefix else f"{self.prefix}/catalog.json"
            try:
                if sync_file(self.client, self.bucket, catalog_key, catalog_path, dry_run):
                    result.uploaded += 1
                else:
                    result.skipped += 1
            except S3UploadError as e:
                result.errors.append(str(e))
            if progress_callback:
                progress_callback("catalog.json", 1)

        return result
