from __future__ import annotations

import typer
from rich import print
from rich.table import Table

from crsm.cli.app import AppContext
from crsm.repo import CrsmRepo

#ls_app = typer.Typer(help="List items")

def ls(
    ctx: typer.Context,
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows"),
):
    """
       List CRSM items.

       Displays items stored in the CRSM database, ordered by most recent
       first. By default, results are shown in a human-readable table.

       Examples:
         crsm ls
         crsm ls --limit 10
         crsm ls --json
    """
    appctx: AppContext = ctx.obj
    repo = CrsmRepo(appctx.db_path)

    rows = repo.list_items(limit=limit)

    table = Table(title="CRSM items")
    table.add_column("id")
    table.add_column("name")
    table.add_column("created")

    for r in rows:
        table.add_row(str(r["id"]), r["name"], r["created_at"])

    print(table)

