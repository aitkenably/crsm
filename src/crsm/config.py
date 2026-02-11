from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import tomllib

APP_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "crsm"
DEFAULT_CONFIG_PATH = APP_DIR / "config.toml"
DEFAULT_DB_PATH = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "crsm" / "crsm.db"

@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    # add more settings here (e.g. default profile, ui prefs, etc.)

def load_config(path: Optional[Path]) -> AppConfig:
    cfg_path = path or DEFAULT_CONFIG_PATH

    db_path = DEFAULT_DB_PATH

    if cfg_path.exists():
        data = tomllib.loads(cfg_path.read_text("utf-8"))
        db_path = Path(data.get("db", {}).get("path", db_path))

    # ensure parent dirs exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    return AppConfig(db_path=db_path)

