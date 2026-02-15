# CRSM Command Contracts

These contracts define the **intended behavior** of each CLI command.

## Global Conventions (apply to all commands)

### Exit codes
- `0` — success
- `1` — user error (bad args, missing file, not found)
- `2` — operational/runtime error (IO, DB, ffmpeg failure, AWS failure)
- `130` — interrupted (Ctrl+C)

### Output
- Human-friendly output by default (tables / concise lines).
- All errors go to **stderr** and include a short actionable hint.

### Config + Paths
- Commands read config from (in priority order):
  1. `--config <path>`
  2. `CRSM_CONFIG`
  3. default: `~/.config/crsm/config.toml` 
- All repo paths are resolved to absolute paths internally.

### Database
- SQLite is the source of truth for catalog entries.
- Any action that changes files must update DB in the same command invocation.
- Commands that change DB should use transactions.

### Idempotency
- Commands should be safe to re-run:
  - If the desired end state already exists, return `0` with a message like “no changes”.

### Required external tooling
- Thumbnail generation assumes `ffmpeg` is available.
- If missing, fail with exit code `2` and a clear remediation message.

---

## `crsm add` — Import a video into the repo

### Purpose
Add a new video to the managed repository: copy/move it in, 
generate a thumbnail, and create a DB entry.

### Synopsis
```
crsm add <path-to-video> [--title TEXT] [--move|--copy] [--force]
[--thumb-at SECONDS]
```

### Inputs
- `path-to-video` (required): must exist and be a file.
- `--title` (optional): if omitted, derive from filename by replacing underscores with spaces and removing extension.
- `--move|--copy` (optional): default `--move`.
- `--force` (optional): overwrite/replace if a matching entry already exists.
- `--thumb-at` (optional): choose thumbnail capture position. Default 60 seconds. 

### Preconditions
- Repo directories exist.
- Video filename collision rules are defined:
  - Default: reject duplicates unless `--force`.

### Side Effects
- Writes a video file into `<repo>/videos/`.
- Writes a thumbnail into `<repo>/thumbnails/`.
- Inserts/updates a row in SQLite.

### Behavior
1. Validate file exists and is a supported media type (by whitelist of extensions).
2. Determine destination filename and paths.
3. If a DB entry already exists for the same destination key:
   - Without `--force`: fail exit `1` with conflict info.
   - With `--force`: replace files + update row.
4. Transfer file (`move` or `copy`) into repo.
5. Generate thumbnail.
6. Write/update DB row in a transaction:
   - If thumbnail generation fails, rollback DB changes and remove partial files.
7. Print a confirmation including title and stored paths.

### Output (default)
- One-line summary:
  - `Added: "<title>" (video: <filename>, thumbnail: <thumbname>)`

### Errors 
* File missing / not a file → exit 1
* Unsupported extension → exit 1
* Repo not writable / IO error → exit 2
* ffmpeg/thumbnail failure → exit 2
* DB failure → exit 2

---
## crsm ls — List catalog entries

### Purpose
List videos known to the database, optionally filtered and sorted.

### Synopsis
``` 
crsm ls [--search TEXT] [--limit N] [--offset N]
        [--sort title|id] [--desc]
        [--fields FIELD,FIELD,...]
```

### Inputs
* --search: substring match on title 
* Pagination via --limit / --offset.
* --sort: sorting by title or id ascending (default) or descending
* --fields: select columns to show (default: id, title).

### Side Effects
* None (read-only).

### Behavior
* Open DB.
* Apply filters and sorting.
* Render output:
  * Default: table with columns like ID | Title | Filename | Added
  * --fields: render only requested columns.

### Errors 
* DB missing/unreadable → exit 2

--- 

## `crsm rm` — Remove a video from the repo and DB

### Purpose

Remove a catalog entry and its associated files.

### Synopsis

```bash
crsm rm <id-or-title> [--keep-files] [--yes] 
```
### Inputs

- `<id-or-title>`:
  - If numeric: treated as database ID
  - Otherwise: treated as title match
- `--keep-files`: remove only from DB, do not delete files
- `--yes`: skip confirmation prompt

### Preconditions

- If title matches multiple entries:
  - Fail with exit `1`
  - Display matching entries
  - Require using ID

### Side Effects

- Deletes video file and thumbnail file (unless `--keep-files`)
- Deletes DB row

### Behavior

1. Resolve target to exactly one DB entry.
2. If not `--yes`, prompt:

```bash
Remove "<title>"? [y/N]
```

3. Execute in a transaction:
- Delete DB entry
- Delete video file
- Delete thumbnail file
4. If file deletion fails:
- DB deletion remains committed
- Print warning
- Exit `2`

### Output

```bash
Removed: "<title>"
```

### Errors 
* Entry not found → exit 1
* Ambiguous title → exit 1
* IO failure → exit 2
* Database failure → exit 2

---

## `crsm live` — Publish repo to S3 and generate catalog

### Purpose

Generate the catalog file from the database and publish videos, thumbnails, and catalog to S3.

### Synopsis
```bash 
crsm live [--dry-run] [--no-sync] [--no-catalog]
          [--bucket NAME] [--prefix PATH]
          [--public-base-url URL]
```
### Inputs
Uses config file defaults:
* S3 bucket
* Optional S3 prefix
* Public base URL

Overrides:
* --bucket
* --prefix
* --public-base-url

Flags:
* --dry-run: show actions without uploading
* --no-sync: only generate catalog locally
* --no-catalog: do not regenerate catalog, only sync assets

### Side Effects
* Writes local catalog file (e.g., catalog.json)
* Uploads videos, thumbnails, and catalog to S3 (unless --dry-run)

### Behavior

1. Load configuration and validate AWS credentials.
2. If catalog enabled:
   * Query DB for all videos
   * Generate catalog entries:
   ```
   video_url = <public_base_url>/<prefix?>/<video_relpath>
   thumb_url = <public_base_url>/<prefix?>/<thumb_relpath>
   ```
   * Write catalog file locally with deterministic ordering (title → id).
3. If sync enabled:
   * Upload videos
   * Upload thumbnails
   * Upload catalog file
   * Prefer incremental sync (mtime/size or checksum).
4. Print summary:
   * uploaded counts
   * skipped counts
   * errors

### Errors 
* Missing or invalid AWS config → exit 1
* AWS credential or permission failure → exit 2
* Upload failure → exit 2
* Catalog write failure → exit 2