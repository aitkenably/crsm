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
DEFAULT_LIBRARY_PATH = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "crsm" / "library"


class ConfigError(Exception):
    """Raised when configuration validation fails."""


@dataclass(frozen=True)
class S3Config:
    bucket: Optional[str] = None
    prefix: Optional[str] = None
    public_base_url: Optional[str] = None


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    library_path: Path
    s3: S3Config = S3Config()


def load_config(path: Optional[Path] = None) -> AppConfig:
    cfg_path = path or DEFAULT_CONFIG_PATH

    logging.info(f"Config file path is {cfg_path}")

    db_path = DEFAULT_DB_PATH
    library_path = DEFAULT_LIBRARY_PATH

    s3_config = S3Config()

    if cfg_path.exists():
        data = tomllib.loads(cfg_path.read_text("utf-8"))
        db_path = Path(data.get("db", {}).get("path", db_path))
        library_path = Path(data.get("library", {}).get("path", library_path))

        s3_data = data.get("s3", {})
        s3_config = S3Config(
            bucket=s3_data.get("bucket"),
            prefix=s3_data.get("prefix"),
            public_base_url=s3_data.get("public_base_url"),
        )

    # Validate that required directories exist
    if not db_path.parent.exists():
        raise ConfigError(f"Database directory does not exist: {db_path.parent}")
    if not library_path.exists():
        raise ConfigError(f"Library directory does not exist: {library_path}")

    return AppConfig(db_path=db_path, library_path=library_path, s3=s3_config)

