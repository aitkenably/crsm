from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from crsm.repo import CrsmRepo
from crsm.catalog import build_catalog, write_catalog


def live(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be uploaded without uploading"
    ),
    no_sync: bool = typer.Option(
        False, "--no-sync", help="Skip S3 sync (catalog only)"
    ),
    no_catalog: bool = typer.Option(
        False, "--no-catalog", help="Skip catalog generation"
    ),
    bucket: Optional[str] = typer.Option(
        None, "--bucket", help="S3 bucket name (overrides config)"
    ),
    prefix: Optional[str] = typer.Option(
        None, "--prefix", help="S3 key prefix (overrides config)"
    ),
    public_base_url: Optional[str] = typer.Option(
        None, "--public-base-url", help="Public base URL for catalog (overrides config)"
    ),
):
    """
    Publish library to S3 and generate catalog.

    Generates a catalog.json file with public URLs for all videos
    and syncs the library (videos, thumbnails, catalog) to AWS S3.
    """
    from crsm.cli.app import AppContext

    app_ctx: AppContext = ctx.obj

    # Resolve config - CLI flags override config file
    s3_bucket = bucket or app_ctx.config.s3.bucket
    s3_prefix = prefix if prefix is not None else app_ctx.config.s3.prefix
    base_url = public_base_url or app_ctx.config.s3.public_base_url

    # Validate required settings
    if not no_sync and not s3_bucket:
        print("[red]Error:[/red] S3 bucket is required for sync. Use --bucket or configure [s3] bucket in config.")
        raise typer.Exit(1)

    if not no_catalog and not base_url:
        print("[red]Error:[/red] Public base URL is required for catalog. Use --public-base-url or configure [s3] public_base_url in config.")
        raise typer.Exit(1)

    # Get all videos from database
    repo = CrsmRepo(app_ctx.db_path)
    videos = repo.get_all_videos()

    if not videos:
        print("[yellow]No videos found in library.[/yellow]")
        raise typer.Exit(0)

    catalog_path = None

    # Generate catalog
    if not no_catalog:
        catalog = build_catalog(videos, base_url, s3_prefix)
        catalog_path = app_ctx.library_path / "catalog.json"
        write_catalog(catalog, catalog_path)
        print(f"[green]Generated catalog:[/green] {catalog_path}")
        logging.info(f"Catalog contains {len(catalog.videos)} videos")

    # Sync to S3
    if not no_sync:
        try:
            from crsm.s3 import (
                get_s3_client,
                S3Publisher,
                S3NotAvailableError,
                S3CredentialsError,
                S3UploadError,
            )
        except ImportError:
            print("[red]Error:[/red] boto3 is not installed. Install with: pip install crsm[s3]")
            raise typer.Exit(1)

        try:
            client = get_s3_client()
        except S3NotAvailableError as e:
            print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except S3CredentialsError as e:
            print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        publisher = S3Publisher(client, s3_bucket, s3_prefix)

        if dry_run:
            print("[yellow]Dry run mode - no files will be uploaded[/yellow]")

        # Calculate total files: video + thumbnail per video, plus catalog if present
        total_files = len(videos) * 2 + (1 if catalog_path else 0)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("{task.fields[current_file]}"),
        ) as progress:
            task = progress.add_task("Syncing to S3...", total=total_files, current_file="")

            def on_progress(filename: str, advance: int):
                progress.update(task, advance=advance, current_file=filename)

            result = publisher.sync_library(
                library_path=app_ctx.library_path,
                videos=videos,
                catalog_path=catalog_path,
                dry_run=dry_run,
                progress_callback=on_progress,
            )

        # Print summary table
        table = Table(title="Sync Summary")
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Uploaded", str(result.uploaded))
        table.add_row("Skipped", str(result.skipped))
        table.add_row("Errors", str(len(result.errors)))

        print(table)

        if result.errors:
            print("[red]Errors:[/red]")
            for error in result.errors:
                print(f"  - {error}")
            raise typer.Exit(2)

    print("[green]Done![/green]")
