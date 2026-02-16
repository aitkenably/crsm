from __future__ import annotations

import sqlite3

import typer
from rich import print
from rich.table import Table

from crsm.cli.app import AppContext
from crsm.repo import CrsmRepo

VALID_FIELDS = {"id", "title", "video_path", "thumbnail_path"}
ALL_FIELDS = ["id", "title", "video_path", "thumbnail_path"]
VALID_SORT = {"id", "title"}


def ls(
    ctx: typer.Context,
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows"),
    offset: int = typer.Option(0, "--offset", help="Skip first N rows"),
    search: str = typer.Option(None, "--search", "-s", help="Filter by title substring"),
    sort: str = typer.Option("id", "--sort", help="Sort by: id or title"),
    desc: bool = typer.Option(False, "--desc", help="Sort descending"),
    fields: str = typer.Option(None, "--fields", "-f", help="Comma-separated columns or '*' for all: id,title,video_path,thumbnail_path"),
):
    """
       List CRSM items.

       Displays items stored in the CRSM database, ordered by most recent
       first. By default, results are shown in a human-readable table.

       Examples:
         crsm ls
         crsm ls --limit 10
         crsm ls --search "Chill"
         crsm ls --sort title --desc
         crsm ls --fields id,title
         crsm ls --fields '*'
    """
    if sort not in VALID_SORT:
        print(f"[red]Error:[/red] Invalid sort value '{sort}'. Must be one of: {', '.join(VALID_SORT)}")
        raise typer.Exit(1)

    if fields:
        if fields.strip() == "*":
            field_list = ALL_FIELDS
        else:
            field_list = [f.strip() for f in fields.split(",")]
            invalid_fields = set(field_list) - VALID_FIELDS
            if invalid_fields:
                print(f"[red]Error:[/red] Invalid field(s): {', '.join(invalid_fields)}. Valid fields: {', '.join(VALID_FIELDS)}")
                raise typer.Exit(1)
    else:
        field_list = ["id", "title"]

    appctx: AppContext = ctx.obj
    repo = CrsmRepo(appctx.db_path)

    try:
        rows = repo.list_video(
            limit=limit,
            offset=offset,
            search=search,
            sort_by=sort,
            descending=desc,
        )
    except sqlite3.Error as e:
        print(f"[red]Database error:[/red] {e}")
        raise typer.Exit(2)

    table = Table()
    for field in field_list:
        table.add_column(field)

    for r in rows:
        table.add_row(*[str(r[field]) for field in field_list])

    print(table)

