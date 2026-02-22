from __future__ import annotations

import shutil
import subprocess

import typer
from rich import print

from crsm.cli.app import AppContext


def db(ctx: typer.Context):
    """
    Open the database in the sqlite3 shell.

    Launches an interactive sqlite3 session with the configured database.

    Example:
      crsm db
    """
    appctx: AppContext = ctx.obj

    # Check if sqlite3 is available
    sqlite3_path = shutil.which("sqlite3")
    if sqlite3_path is None:
        print("[red]Error:[/red] sqlite3 command not found in PATH")
        raise typer.Exit(2)

    # Launch sqlite3 with the database
    subprocess.run([sqlite3_path, str(appctx.db_path)])
