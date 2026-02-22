from __future__ import annotations

import logging
import platform
import sqlite3
import subprocess
from pathlib import Path

import typer
from PIL import Image
from rich import print
from rich.table import Table

from crsm.cli.app import AppContext
from crsm.library import CrsmLibrary
from crsm.repo import CrsmRepo


def thumbnail(
    ctx: typer.Context,
    id_or_title: str = typer.Argument(..., help="Video ID (numeric) or title"),
    view: bool = typer.Option(False, "--view", help="Open thumbnail in default image viewer"),
):
    """
    Inspect (and optionally view) a video thumbnail.

    Display metadata for the thumbnail image associated with a catalog entry,
    including its resolution. Optionally launch the thumbnail image in the
    system's default image viewer.

    If the argument is numeric, it's treated as a video ID.
    Otherwise, it's treated as an exact title match.

    Examples:
      crsm thumbnail 1
      crsm thumbnail "Chill Beats"
      crsm thumbnail 1 --view
    """
    appctx: AppContext = ctx.obj
    repo = CrsmRepo(appctx.db_path)
    library = CrsmLibrary(appctx.library_path)

    try:
        video = _resolve_video(repo, id_or_title)
    except VideoNotFoundError as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except AmbiguousTitleError as e:
        print(f"[red]Error:[/red] {e.message}")
        _display_matches(e.matches)
        print("\nUse the video ID to inspect a specific entry.")
        raise typer.Exit(1)
    except sqlite3.Error as e:
        print(f"[red]Database error:[/red] {e}")
        logging.debug(f"SQLite error: {e}")
        raise typer.Exit(2)

    thumbnail_path = video["thumbnail_path"]

    # Get full path and verify file exists
    full_path = library.get_full_path(thumbnail_path)
    if not full_path.exists():
        print(f"[red]Error:[/red] Thumbnail file not found: {full_path}")
        raise typer.Exit(2)

    # Read image metadata
    try:
        metadata = _read_image_metadata(full_path)
    except Exception as e:
        print(f"[red]Error:[/red] Failed to read image metadata: {e}")
        logging.debug(f"Image metadata error: {e}")
        raise typer.Exit(2)

    # Print metadata
    print(f"Thumbnail: [green]{thumbnail_path}[/green]")
    print(f"Resolution: [green]{metadata['width']}x{metadata['height']}[/green]")
    print(f"Format: [green]{metadata['format']}[/green]")
    print(f"Size: [green]{metadata['size']}[/green]")

    # Optionally launch viewer
    if view:
        try:
            _launch_file(full_path)
        except RuntimeError as e:
            print(f"[red]Error:[/red] {e}")
            raise typer.Exit(2)


class VideoNotFoundError(Exception):
    pass


class AmbiguousTitleError(Exception):
    def __init__(self, message: str, matches: list):
        self.message = message
        self.matches = matches
        super().__init__(message)


def _resolve_video(repo: CrsmRepo, id_or_title: str):
    """Resolve id_or_title to exactly one video entry."""
    if id_or_title.isdigit():
        video_id = int(id_or_title)
        video = repo.get_video_by_id(video_id)
        if video is None:
            raise VideoNotFoundError(f"Video with ID {video_id} not found")
        return video
    else:
        matches = repo.get_videos_by_title(id_or_title)
        if len(matches) == 0:
            raise VideoNotFoundError(f'Video with title "{id_or_title}" not found')
        if len(matches) > 1:
            raise AmbiguousTitleError(
                f'Multiple videos found with title "{id_or_title}"',
                matches
            )
        return matches[0]


def _display_matches(matches: list):
    """Display a table of matching videos."""
    table = Table(title="Matching videos")
    table.add_column("id")
    table.add_column("title")
    for m in matches:
        table.add_row(str(m["id"]), m["title"])
    print(table)


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.0f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    else:
        return f"{size_bytes} B"


def _read_image_metadata(path: Path) -> dict:
    """Read image metadata from file."""
    with Image.open(path) as img:
        width, height = img.size
        img_format = img.format.lower() if img.format else "unknown"

    file_size = path.stat().st_size

    return {
        "width": width,
        "height": height,
        "format": img_format,
        "size": _format_file_size(file_size),
    }


def _launch_file(path: Path) -> None:
    """Launch a file with the system's default application."""
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif system == "Linux":
        subprocess.Popen(["xdg-open", str(path)])
    elif system == "Windows":
        subprocess.Popen(["start", "", str(path)], shell=True)
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
