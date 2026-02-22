from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich import print

from crsm.cli.app import AppContext
from crsm.db import get_connection
from crsm.library import CrsmLibrary
from crsm.repo import CrsmRepo
from crsm.s3 import BOTO3_AVAILABLE


@dataclass
class CheckResult:
    ok: bool
    message: str


@dataclass
class DoctorReport:
    results: list[CheckResult] = field(default_factory=list)
    passed: int = 0
    errors: int = 0

    def add(self, result: CheckResult) -> None:
        self.results.append(result)
        if result.ok:
            self.passed += 1
        else:
            self.errors += 1

    def ok(self, message: str) -> None:
        self.add(CheckResult(ok=True, message=message))

    def error(self, message: str) -> None:
        self.add(CheckResult(ok=False, message=message))


def check_configuration(appctx: AppContext, check_aws: bool) -> list[CheckResult]:
    """Phase 1: Configuration checks."""
    results = []

    # Config is already loaded by app callback, so if we got here it's OK
    results.append(CheckResult(ok=True, message="Config file loaded"))

    # Check AWS-related config if needed
    if check_aws:
        if appctx.config.s3.bucket:
            results.append(CheckResult(ok=True, message="S3 bucket configured"))
        else:
            results.append(CheckResult(ok=False, message="S3 bucket not configured"))

        if appctx.config.s3.public_base_url:
            results.append(CheckResult(ok=True, message="Public base URL configured"))
        else:
            results.append(CheckResult(ok=False, message="Public base URL not configured"))

    return results


def check_filesystem(appctx: AppContext) -> list[CheckResult]:
    """Phase 2: Filesystem checks."""
    results = []
    library = CrsmLibrary(appctx.library_path)

    # Check library path exists
    if appctx.library_path.exists():
        results.append(CheckResult(ok=True, message=f"Library path exists: {appctx.library_path}"))
    else:
        results.append(CheckResult(ok=False, message=f"Library path does not exist: {appctx.library_path}"))
        return results  # Can't continue without library path

    # Check videos directory
    if library.videos_dir.exists():
        results.append(CheckResult(ok=True, message="Videos directory exists"))
        if _is_writable(library.videos_dir):
            results.append(CheckResult(ok=True, message="Videos directory writable"))
        else:
            results.append(CheckResult(ok=False, message="Videos directory not writable"))
    else:
        results.append(CheckResult(ok=False, message=f"Videos directory does not exist: {library.videos_dir}"))

    # Check thumbnails directory
    if library.thumbnails_dir.exists():
        results.append(CheckResult(ok=True, message="Thumbnails directory exists"))
        if _is_writable(library.thumbnails_dir):
            results.append(CheckResult(ok=True, message="Thumbnails directory writable"))
        else:
            results.append(CheckResult(ok=False, message="Thumbnails directory not writable"))
    else:
        results.append(CheckResult(ok=False, message=f"Thumbnails directory does not exist: {library.thumbnails_dir}"))

    # Check database file or parent directory
    if appctx.db_path.exists():
        results.append(CheckResult(ok=True, message="Database file exists"))
    elif _is_writable(appctx.db_path.parent):
        results.append(CheckResult(ok=True, message="Database parent directory writable"))
    else:
        results.append(CheckResult(ok=False, message=f"Database parent directory not writable: {appctx.db_path.parent}"))

    return results


def _is_writable(path: Path) -> bool:
    """Check if a directory is writable."""
    import os
    return os.access(path, os.W_OK)


def check_external_tools() -> list[CheckResult]:
    """Phase 3: External tooling checks."""
    results = []

    # Check if ffmpeg is in PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        results.append(CheckResult(ok=False, message="ffmpeg not found in PATH"))
        return results

    # Check if ffmpeg is executable
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            results.append(CheckResult(ok=True, message="ffmpeg available"))
        else:
            results.append(CheckResult(ok=False, message="ffmpeg found but not executable"))
    except (subprocess.TimeoutExpired, OSError) as e:
        results.append(CheckResult(ok=False, message=f"ffmpeg check failed: {e}"))

    return results


def check_database(appctx: AppContext) -> list[CheckResult]:
    """Phase 4: Database integrity checks."""
    results = []

    try:
        conn = get_connection(appctx.db_path)
        results.append(CheckResult(ok=True, message="Database opens successfully"))

        # Check if videos table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='videos'"
        )
        if cursor.fetchone():
            results.append(CheckResult(ok=True, message="Videos table exists"))
        else:
            results.append(CheckResult(ok=False, message="Videos table does not exist"))

        conn.close()
    except Exception as e:
        results.append(CheckResult(ok=False, message=f"Database error: {e}"))

    return results


def check_repository_consistency(appctx: AppContext) -> list[CheckResult]:
    """Phase 5: Repository consistency checks."""
    results = []
    library = CrsmLibrary(appctx.library_path)
    repo = CrsmRepo(appctx.db_path)

    try:
        videos = repo.get_all_videos()
    except Exception as e:
        results.append(CheckResult(ok=False, message=f"Failed to query videos: {e}"))
        return results

    # Track files referenced in DB
    db_video_files = set()
    db_thumbnail_files = set()

    # Check each DB entry has valid files
    for video in videos:
        video_id = video["id"]
        video_path = video["video_path"]
        thumbnail_path = video["thumbnail_path"]

        # Check for null fields
        if not video_path:
            results.append(CheckResult(ok=False, message=f"Null video_path for ID {video_id}"))
        else:
            db_video_files.add(video_path)
            # Check video file exists
            full_video_path = library.get_full_path(video_path)
            if not full_video_path.exists():
                results.append(CheckResult(ok=False, message=f"Missing video file for ID {video_id}: {video_path}"))

        if not thumbnail_path:
            results.append(CheckResult(ok=False, message=f"Null thumbnail_path for ID {video_id}"))
        else:
            db_thumbnail_files.add(thumbnail_path)
            # Check thumbnail file exists
            full_thumbnail_path = library.get_full_path(thumbnail_path)
            if not full_thumbnail_path.exists():
                results.append(CheckResult(ok=False, message=f"Missing thumbnail for ID {video_id}: {thumbnail_path}"))

    # Check for orphaned video files
    if library.videos_dir.exists():
        for video_file in library.videos_dir.iterdir():
            if video_file.is_file():
                relative_path = f"videos/{video_file.name}"
                if relative_path not in db_video_files:
                    results.append(CheckResult(ok=False, message=f"Orphaned video file: {relative_path}"))

    # Check for orphaned thumbnail files
    if library.thumbnails_dir.exists():
        for thumb_file in library.thumbnails_dir.iterdir():
            if thumb_file.is_file():
                relative_path = f"thumbnails/{thumb_file.name}"
                if relative_path not in db_thumbnail_files:
                    results.append(CheckResult(ok=False, message=f"Orphaned thumbnail file: {relative_path}"))

    # If no issues found, report OK
    if not results:
        results.append(CheckResult(ok=True, message="Repository consistency check passed"))

    return results


def check_aws(appctx: AppContext) -> list[CheckResult]:
    """Phase 6: AWS publishing readiness checks."""
    results = []

    # Check boto3 is available
    if not BOTO3_AVAILABLE:
        results.append(CheckResult(ok=False, message="boto3 not installed (pip install crsm[s3])"))
        return results

    results.append(CheckResult(ok=True, message="boto3 available"))

    # Check AWS credentials using STS GetCallerIdentity
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

        sts = boto3.client("sts")
        sts.get_caller_identity()
        results.append(CheckResult(ok=True, message="AWS credentials valid"))
    except NoCredentialsError:
        results.append(CheckResult(ok=False, message="AWS credentials not found"))
        return results
    except PartialCredentialsError:
        results.append(CheckResult(ok=False, message="Incomplete AWS credentials"))
        return results
    except ClientError as e:
        results.append(CheckResult(ok=False, message=f"AWS credentials invalid: {e}"))
        return results
    except Exception as e:
        results.append(CheckResult(ok=False, message=f"AWS credential check failed: {e}"))
        return results

    # Check S3 bucket is reachable
    bucket = appctx.config.s3.bucket
    if bucket:
        try:
            s3 = boto3.client("s3")
            s3.head_bucket(Bucket=bucket)
            results.append(CheckResult(ok=True, message=f"S3 bucket reachable: {bucket}"))
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                results.append(CheckResult(ok=False, message=f"S3 bucket not found: {bucket}"))
            elif error_code == "403":
                results.append(CheckResult(ok=False, message=f"S3 bucket access denied: {bucket}"))
            else:
                results.append(CheckResult(ok=False, message=f"S3 bucket check failed: {e}"))
        except Exception as e:
            results.append(CheckResult(ok=False, message=f"S3 bucket check failed: {e}"))

    return results


def doctor(
    ctx: typer.Context,
    no_aws: bool = typer.Option(False, "--no-aws", help="Skip AWS credential and S3 bucket checks"),
):
    """
    Validate system configuration and repository health.

    Performs read-only diagnostics across configuration, filesystem,
    external tools, database, repository consistency, and AWS readiness.
    """
    appctx: AppContext = ctx.obj
    report = DoctorReport()
    check_aws_flag = not no_aws

    # Phase 1: Configuration
    for result in check_configuration(appctx, check_aws_flag):
        report.add(result)

    # Phase 2: Filesystem
    for result in check_filesystem(appctx):
        report.add(result)

    # Phase 3: External Tooling
    for result in check_external_tools():
        report.add(result)

    # Phase 4: Database Integrity
    for result in check_database(appctx):
        report.add(result)

    # Phase 5: Repository Consistency
    for result in check_repository_consistency(appctx):
        report.add(result)

    # Phase 6: AWS Publishing Readiness
    if check_aws_flag:
        for result in check_aws(appctx):
            report.add(result)

    # Print results
    for result in report.results:
        if result.ok:
            print(f"[green][OK][/green] {result.message}")
        else:
            print(f"[red][ERROR][/red] {result.message}")

    # Print summary
    print()
    print("Summary:")
    print(f"  Passed: {report.passed}")
    print(f"  Errors: {report.errors}")

    # Exit with appropriate code
    if report.errors > 0:
        raise typer.Exit(1)
