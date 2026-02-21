from __future__ import annotations

import logging
import platform
import sqlite3
import subprocess

import typer
from rich import print
from rich.table import Table

from crsm.cli.app import AppContext
from crsm.library import CrsmLibrary
from crsm.repo import CrsmRepo


def play(
    ctx: typer.Context,
    id_or_title: str = typer.Argument(..., help="Video ID (numeric) or title"),
):
    """
    Play a video from the library.

    If the argument is numeric, it's treated as a video ID.
    Otherwise, it's treated as an exact title match.

    Examples:
      crsm play 1
      crsm play "Chill Beats"
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
        print("\nUse the video ID to play a specific entry.")
        raise typer.Exit(1)
    except sqlite3.Error as e:
        print(f"[red]Database error:[/red] {e}")
        logging.debug(f"SQLite error: {e}")
        raise typer.Exit(2)

    video_title = video["title"]
    video_path = video["video_path"]

    # Get full path and verify file exists
    full_path = library.get_full_path(video_path)
    if not full_path.exists():
        print(f"[red]Error:[/red] Video file not found: {full_path}")
        raise typer.Exit(2)

    # Launch the video with the system default application
    try:
        _launch_file(full_path)
    except RuntimeError as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2)

    print(f'Playing: "{video_title}"')


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


def _launch_file(path) -> None:
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
