from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import tomllib
import logging

APP_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "crsm"
DEFAULT_CONFIG_PATH = APP_DIR / "config.toml"
DEFAULT_DB_PATH = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "crsm" / "crsm.db"
DEFAULT_REPO_PATH = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "crsm" / "library"

@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    repo_path: Path

def load_config(path: Optional[Path] = None) -> AppConfig:
    cfg_path = path or DEFAULT_CONFIG_PATH

    db_path = DEFAULT_DB_PATH
    repo_path = DEFAULT_REPO_PATH

    if cfg_path.exists():
        data = tomllib.loads(cfg_path.read_text("utf-8"))
        db_path = Path(data.get("db", {}).get("path", db_path))
        repo_path = Path(data.get("repo", {}).get("path", repo_path))

    # ensure parent dirs exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    repo_path.mkdir(parents=True, exist_ok=True)

    logging.info(f"Reading configuration from {cfg_path}")
    logging.info(f"Database path is {db_path}")
    logging.info(f"Repository path is {repo_path}")

    return AppConfig(db_path=db_path, repo_path=repo_path)

