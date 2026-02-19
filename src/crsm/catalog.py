from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class CatalogEntry:
    id: int
    title: str
    video_url: str
    thumbnail_url: str


@dataclass
class Catalog:
    videos: list[CatalogEntry]

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {"videos": [asdict(entry) for entry in self.videos]},
            indent=indent,
        )


def build_catalog(
    videos: list,
    public_base_url: str,
    prefix: Optional[str] = None,
) -> Catalog:
    """
    Build a catalog from video records.

    Args:
        videos: List of video records (dict-like with id, title, video_path, thumbnail_path)
        public_base_url: Base URL for public access (e.g., https://cdn.example.com)
        prefix: Optional path prefix (e.g., "media")

    Returns:
        Catalog instance with sorted entries
    """
    # Remove trailing slash from base URL if present
    base_url = public_base_url.rstrip("/")

    # Build prefix path
    prefix_path = f"/{prefix.strip('/')}" if prefix else ""

    entries = []
    for video in videos:
        video_filename = Path(video["video_path"]).name
        thumbnail_filename = Path(video["thumbnail_path"]).name

        entry = CatalogEntry(
            id=video["id"],
            title=video["title"],
            video_url=f"{base_url}{prefix_path}/videos/{video_filename}",
            thumbnail_url=f"{base_url}{prefix_path}/thumbnails/{thumbnail_filename}",
        )
        entries.append(entry)

    # Sort by title, then by id as tiebreaker
    entries.sort(key=lambda e: (e.title.lower(), e.id))

    return Catalog(videos=entries)


def write_catalog(catalog: Catalog, output_path: Path) -> None:
    """Write catalog to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(catalog.to_json(), encoding="utf-8")
