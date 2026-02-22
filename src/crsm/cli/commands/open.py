from __future__ import annotations

import platform
import subprocess

import typer
from rich import print

from crsm.cli.app import AppContext


def open_library(ctx: typer.Context):
    """
    Open the library folder in the system file browser.

    Launches Finder (macOS), file explorer (Windows), or the default
    file manager (Linux) to browse the library directory.

    Example:
      crsm open
    """
    appctx: AppContext = ctx.obj

    try:
        _launch_folder(appctx.library_path)
    except RuntimeError as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2)

    print(f"Opened: {appctx.library_path}")


def _launch_folder(path) -> None:
    """Launch a folder with the system's default file browser."""
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif system == "Linux":
        subprocess.Popen(["xdg-open", str(path)])
    elif system == "Windows":
        subprocess.Popen(["explorer", str(path)])
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
