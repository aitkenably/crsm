# src/crsm/cli/app.py
from __future__ import annotations

import logging
import sqlite3

import typer
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich import print

from crsm.config import load_config, AppConfig, ConfigError
from crsm.db import ensure_schema
from crsm.logging_utils import configure_logging

app = typer.Typer(no_args_is_help=True, help="coder-radio Station Manager CLI")


@dataclass
class AppContext:
    config: AppConfig
    db_path: Path
    library_path: Path


@app.callback()
def main_callback(
    ctx: typer.Context,
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    db_path: Optional[Path] = typer.Option(
        None, "--db", help="Path to SQLite database file"
    ),
    library_path: Optional[Path] = typer.Option(
        None, "--library", "-l", help="Path to video library directory"
    ),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Increase verbosity (-v, -vv)"
    ),
):
    configure_logging(verbose=verbose)

    if config_path is not None and not config_path.exists():
        print(f"[red]Error:[/red] Config file does not exist: {config_path}")
        raise typer.Exit(1)

    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)

    final_db_path = db_path or config.db_path
    final_library_path = library_path or config.library_path

    if not final_db_path.parent.exists():
        print(f"[red]Error:[/red] Database directory does not exist: {final_db_path.parent}")
        raise typer.Exit(1)

    if not final_library_path.exists():
        print(f"[red]Error:[/red] Library directory does not exist: {final_library_path}")
        raise typer.Exit(1)

    logging.info(f"Database path is {final_db_path}")
    logging.info(f"Library path is {final_library_path}")

    try:
        ensure_schema(final_db_path)
    except sqlite3.DatabaseError as e:
        print(f"[red]Database error:[/red] Invalid or corrupt database file: {final_db_path}")
        logging.debug(f"SQLite DatabaseError: {e}")
        raise typer.Exit(2)
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        if "readonly" in error_msg or "permission" in error_msg:
            print(f"[red]Database error:[/red] Cannot write to database file: {final_db_path}")
        else:
            print(f"[red]Database error:[/red] {e}")
        logging.debug(f"SQLite OperationalError: {e}")
        raise typer.Exit(2)
    except sqlite3.Error as e:
        print(f"[red]Database error:[/red] {e}")
        logging.debug(f"SQLite Error: {e}")
        raise typer.Exit(2)

    ctx.obj = AppContext(config=config, db_path=final_db_path, library_path=final_library_path)

def main() -> None:
    app()

# Register subcommands
#from crsm.cli.commands.add import add_app
from crsm.cli.commands.ls import ls
#from crsm.cli.commands.rm import rm_app
#from crsm.cli.commands.live import live_app

app.command("ls")(ls)

#app.add_typer(add_app, name="add")
#app.add_typer(ls_app, name="ls")
#app.add_typer(rm_app, name="rm")
#app.add_typer(live_app, name="live")

