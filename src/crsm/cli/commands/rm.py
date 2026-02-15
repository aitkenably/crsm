from __future__ import annotations

import logging
import sqlite3

import typer
from rich import print
from rich.table import Table

from crsm.cli.app import AppContext
from crsm.repo import CrsmRepo


def rm(
    ctx: typer.Context,
    id_or_title: str = typer.Argument(..., help="Video ID (numeric) or title"),
    keep_files: bool = typer.Option(False, "--keep-files", help="Only remove from DB, keep files"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Remove a video from the repository.

    If the argument is numeric, it's treated as a video ID.
    Otherwise, it's treated as an exact title match.

    Examples:
      crsm rm 1
      crsm rm "Chill Beats"
      crsm rm 1 --yes
      crsm rm 1 --keep-files
    """
    appctx: AppContext = ctx.obj
    repo = CrsmRepo(appctx.db_path)

    try:
        video = _resolve_video(repo, id_or_title)
    except VideoNotFoundError as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except AmbiguousTitleError as e:
        print(f"[red]Error:[/red] {e.message}")
        _display_matches(e.matches)
        print("\nUse the video ID to remove a specific entry.")
        raise typer.Exit(1)
    except sqlite3.Error as e:
        print(f"[red]Database error:[/red] {e}")
        logging.debug(f"SQLite error: {e}")
        raise typer.Exit(2)

    video_id = video["id"]
    video_title = video["title"]

    if not yes:
        confirmed = typer.confirm(f'Remove "{video_title}"?', default=False)
        if not confirmed:
            print("Cancelled.")
            raise typer.Exit(0)

    try:
        removed = repo.remove_video(video_id)
    except sqlite3.Error as e:
        print(f"[red]Database error:[/red] {e}")
        logging.debug(f"SQLite error during removal: {e}")
        raise typer.Exit(2)

    if not removed:
        print(f"[red]Error:[/red] Video not found (may have been already removed)")
        raise typer.Exit(1)

    if not keep_files:
        logging.warning("File deletion not yet implemented (schema lacks file paths)")

    print(f'Removed: "{video_title}"')


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
