# CRSM Product Overview

## 1. Elevator Pitch

**crsm (coder-radio Station Manager)** is a command-line application for managing a 
local library of video files and thumbnails, synchronizing that library to AWS S3, and 
generating a machine-readable catalog describing the collection.

It automates ingestion, thumbnail generation, cataloging, and publishing so video 
libraries can be hosted statically and consumed by external applications.

---

## 2. Core Responsibilities

crsm is responsible for:

- Importing video files into a managed local repository
- Generating thumbnail images for videos
- Maintaining metadata about videos in a SQLite database
- Generating a catalog file from that database
- Syncing video and thumbnail assets to an AWS S3 bucket

crsm is **not** responsible for:

- Playing videos
- Providing a web UI
- Serving content directly (S3 + external clients handle that)
- Managing AWS infrastructure

---

## 3. High-Level Architecture

### Local Components

- **Video Repository**
  - Directory containing video files
  - Directory containing generated thumbnails

- **SQLite Database**
  - Stores catalog metadata (title, filename, paths, timestamps, etc.)

- **Config File**
  - Defines local repo paths
  - Defines S3 bucket and public base URL
  - Controls thumbnail generation parameters

### Remote Components

- **AWS S3 Bucket**
  - Stores synced video files
  - Stores synced thumbnails
  - Hosts generated catalog file

---

## 4. Primary User Workflow

User adds a video via `crsm add`

crsm:
  - Moves the file into the managed repo
  - Generates a thumbnail
  - Inserts metadata into SQLite 

User optionally runs `crsm live`

crsm:
  - Syncs repo contents to S3
  - Generates a catalog file
  - Uploads the catalog file

External clients consume the catalog file to discover videos and thumbnails.

---

## 5. Domain Concepts

### Video

A managed media asset with:

- Title
- Filename
- Local path
- Local Thumbnail path

### Repository

A local directory tree containing:

```
videos/
thumbnails/
catalog.json
```

### Catalog

A generated file (JSON) listing all videos with:

- Title
- Public video URL
- Public thumbnail URL

This file is derived entirely from the SQLite database.

---

## 6. CLI Commands (Initial Scope)

| Command | Purpose |
|--------|---------|
| `crsm add` | Import video into repo and database |
| `crsm ls` | List catalog entries |
| `crsm rm` | Remove video and metadata |
| `crsm live` | Sync assets and publish catalog |

---

## 7. Success Criteria

- Adding a video requires one command
- Thumbnail generation is automatic
- Catalog generation is deterministic from DB
- S3 sync produces a browsable static library
- No manual file movement required

---

## 8. Constraints

### Technical

- CLI-only (no GUI)
- SQLite for catalog storage
- Local filesystem is source of truth
- S3 is treated as a publish target

### Design

- Idempotent operations where possible
- Explicit commands (no background daemons)
- Predictable directory layout
- Human-readable catalog format

---