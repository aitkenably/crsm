# src/crsm/cli/app.py
from __future__ import annotations

import typer
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from crsm.config import load_config, AppConfig
from crsm.db import get_connection, ensure_schema
from crsm.logging_utils import configure_logging

app = typer.Typer(no_args_is_help=True, help="coder-radio Station Manager CLI")

@dataclass
class AppContext:
    config: AppConfig
    db_path: Path

@app.callback()
def main_callback(
    ctx: typer.Context,
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    db_path: Optional[Path] = typer.Option(
        None, "--db", help="Path to SQLite database file"
    ),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Increase verbosity (-v, -vv)"
    ),
):
    configure_logging(verbose=verbose)

    config = load_config(config_path)
    final_db_path = db_path or config.db_path
    ensure_schema(final_db_path)

    ctx.obj = AppContext(config=config, db_path=final_db_path)

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

