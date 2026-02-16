from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import typer
from rich import print

from crsm.cli.app import AppContext
from crsm.library import CrsmLibrary, ThumbnailGenerationError
from crsm.repo import CrsmRepo


def derive_title_from_filename(filename: str) -> str:
    """Derive a title from a filename by removing extension and replacing underscores."""
    stem = Path(filename).stem
    return stem.replace("_", " ")


def get_destination_filenames(source_path: Path) -> tuple[str, str]:
    """Get destination filenames for video and thumbnail."""
    video_filename = source_path.name
    thumb_filename = source_path.stem + ".png"
    return video_filename, thumb_filename


def add(
    ctx: typer.Context,
    source: Path = typer.Argument(..., help="Path to video file to add"),
    title: Optional[str] = typer.Option(
        None, "--title", "-t", help="Title for the video (default: derived from filename)"
    ),
    move: bool = typer.Option(
        False, "--move/--copy", help="Move file or copy it (default)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing entry"
    ),
    thumb_at: int = typer.Option(
        60, "--thumb-at", help="Thumbnail capture position in seconds"
    ),
):
    """
    Add a video to the library.

    Imports the video file, generates a thumbnail, and creates a database entry.

    Examples:
      crsm add /path/to/video.webm
      crsm add /path/to/video.webm --move
      crsm add /path/to/video.webm --title "My Video"
      crsm add /path/to/video.webm --force
      crsm add /path/to/video.webm --thumb-at 120
    """
    appctx: AppContext = ctx.obj
    library = CrsmLibrary(appctx.library_path)
    repo = CrsmRepo(appctx.db_path)

    # Validate source file exists
    if not source.exists():
        print(f"[red]Error:[/red] File not found: {source}")
        raise typer.Exit(1)

    if not source.is_file():
        print(f"[red]Error:[/red] Not a file: {source}")
        raise typer.Exit(1)

    # Validate file extension
    if not library.is_supported_extension(source):
        from crsm.library import SUPPORTED_VIDEO_EXTENSIONS
        print(f"[red]Error:[/red] Unsupported file type: {source.suffix}")
        print(f"Supported types: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}")
        raise typer.Exit(1)

    # Determine filenames and relative paths
    video_filename, thumb_filename = get_destination_filenames(source)
    video_path = library.get_relative_video_path(video_filename)
    thumb_path = library.get_relative_thumbnail_path(thumb_filename)
    final_title = title if title else derive_title_from_filename(video_filename)

    # Check for conflicts
    existing = repo.get_video_by_path(video_path)
    if existing and not force:
        print(f"[red]Error:[/red] Video already exists: {video_path}")
        print(f"Use --force to overwrite the existing entry (ID: {existing['id']})")
        raise typer.Exit(1)

    # If --force and existing, delete old files first
    if existing and force:
        logging.info(f"Force mode: removing existing entry ID {existing['id']}")
        library.delete_video_files(
            existing["video_path"], existing["thumbnail_path"]
        )
        repo.remove_video(existing["id"])

    # Import video
    try:
        library.import_video(source, video_filename, move=move)
    except FileExistsError as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except OSError as e:
        print(f"[red]Error:[/red] Failed to import video: {e}")
        raise typer.Exit(2)

    # Generate thumbnail
    try:
        library.generate_thumbnail(video_filename, thumb_filename, timestamp=thumb_at)
    except ThumbnailGenerationError as e:
        # Rollback: delete the imported video
        logging.error(f"Thumbnail generation failed, rolling back video import")
        try:
            library.delete_file(video_path)
        except OSError as rollback_error:
            logging.error(f"Rollback failed: {rollback_error}")
        print(f"[red]Error:[/red] Thumbnail generation failed: {e}")
        raise typer.Exit(2)
    except FileNotFoundError as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2)

    # Insert database entry with relative paths
    try:
        video_id = repo.add_video(final_title, video_path, thumb_path)
    except sqlite3.Error as e:
        # Rollback: delete video and thumbnail
        logging.error(f"Database insert failed, rolling back files")
        try:
            library.delete_video_files(video_path, thumb_path)
        except OSError as rollback_error:
            logging.error(f"Rollback failed: {rollback_error}")
        print(f"[red]Database error:[/red] {e}")
        raise typer.Exit(2)

    print(f'Added: "{final_title}" (video: {video_path}, thumbnail: {thumb_path})')
