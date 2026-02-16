# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CRSM (coder-radio Station Manager) is a Python CLI for managing a local library of video files and thumbnails. It handles video ingestion, thumbnail generation, SQLite metadata storage, and AWS S3 publishing.

## Development Commands

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies (pytest)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest src/tests/unit/test_repo.py

# Run a specific test
pytest src/tests/unit/test_repo.py::test_list_video_returns_empty_list

# Run CLI directly
crsm ls
crsm ls -v      # verbose
crsm ls -vv     # debug

# Run CLI via module
python -m crsm ls
```

## Architecture

The codebase follows a layered architecture:

```
CLI Layer (cli/commands/)     <- Thin Typer handlers, delegates to repo
    ↓
Repository Layer (repo.py)    <- Business logic and data access
    ↓
Database Layer (db.py)        <- SQLite schema, connections, WAL mode
    ↓
Config Layer (config.py)      <- TOML config, XDG-compliant paths
```

**Key design principles:**
- CLI layer is thin; business logic lives in `repo.py` for testability
- Database access centralized in `db.py` with dict-like row access
- Configuration uses frozen dataclasses for immutability
- Default paths: `~/.config/crsm/config.toml` and `~/.local/state/crsm/crsm.db`

## Current Implementation Status

- **Implemented:** `crsm ls` (lists videos), `crsm add` (imports videos, copies by default), `crsm rm` (removes videos)
- **Stubbed:** `live` command
- **Database schema:** videos table with id, title, video_path, thumbnail_path columns

## Testing

Tests use pytest with fixtures defined in `src/tests/conftest.py`:
- `cli_runner` - Typer CliRunner instance
- `temp_db_path` - Fresh temporary database
- `seeded_db_path` - Database with sample data

## Tech Stack

- Python 3.11+, Typer (CLI), Rich (output), SQLite3, TOML config
- Planned: ffmpeg (thumbnails), boto3 (S3 sync)
