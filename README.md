# CRSM 

coder-radio Station Manager is a command-line tool for managing a local library of video files and thumbnails, 
synchronizing to AWS S3, and generating a machine-readable catalog.

CRSM automates video ingestion, thumbnail generation, cataloging, and publishing so video libraries can be 
hosted statically and consumed by external applications.

## Features

- Import video files with automatic thumbnail generation
- SQLite-backed metadata storage
- JSON catalog generation with public URLs
- Incremental S3 sync (only uploads changed files)
- XDG-compliant default paths

## Requirements

- Python 3.11+
- ffmpeg (for thumbnail generation)
- AWS credentials (for S3 sync)

## Installation

```bash
# Clone the repository
git clone https://github.com/youruser/crsm.git
cd crsm

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

```

## Configuration

CRSM uses a TOML configuration file. By default, it looks for `~/.config/crsm/config.toml`.

```toml
[db]
path = "/path/to/crsm.db"

[library]
path = "/path/to/library"

[s3]
bucket = "your-bucket-name"
public_base_url = "https://cdn.example.com"
prefix = "media"  # optional
```

### Default Paths

If no config file exists, CRSM uses XDG-compliant defaults:

- Config: `~/.config/crsm/config.toml`
- Database: `~/.local/state/crsm/crsm.db`
- Library: `~/.local/share/crsm/library`

## Usage

### Add a video

```bash
# Add a video (copies by default)
crsm add /path/to/video.mp4

# Add with a custom title
crsm add /path/to/video.mp4 --title "My Video Title"

# Move instead of copy
crsm add /path/to/video.mp4 --move

# Overwrite existing entry
crsm add /path/to/video.mp4 --force

# Custom thumbnail timestamp (default: 60s)
crsm add /path/to/video.mp4 --thumb-at 30
```

### List videos

```bash
# List all videos
crsm ls

# Search by title
crsm ls --search "keyword"

# Sort by title descending
crsm ls --sort title --desc

# Show specific fields
crsm ls --fields id,title,video_path

# Pagination
crsm ls --limit 10 --offset 20
```

### Remove a video

```bash
# Remove by ID
crsm rm 42

# Remove by title
crsm rm "My Video Title"

# Skip confirmation
crsm rm 42 --yes

# Keep files, only remove from database
crsm rm 42 --keep-files
```

### Publish to S3

```bash
# Sync to S3 and generate catalog
crsm live

# Preview what would be uploaded
crsm live --dry-run

# Generate catalog only (no S3 sync)
crsm live --no-sync

# Sync only (no catalog generation)
crsm live --no-catalog

# Override config values
crsm live --bucket my-bucket --public-base-url https://cdn.example.com
```

### Verbose output

```bash
crsm -v ls      # INFO level
crsm -vv ls     # DEBUG level
crsm -vvv ls    # DEBUG level including third-party libraries
```

## Development

### Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running tests

```bash
# Run all tests
pytest

# Run a specific test file
pytest src/tests/unit/test_repo.py

# Run a specific test
pytest src/tests/unit/test_repo.py::test_list_video_returns_empty_list

# Run with verbose output
pytest -v
```