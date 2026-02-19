from __future__ import annotations

import json
from pathlib import Path

from crsm.catalog import CatalogEntry, Catalog, build_catalog, write_catalog


def test_catalog_entry_fields():
    entry = CatalogEntry(
        id=1,
        title="Test Video",
        video_url="https://example.com/videos/test.webm",
        thumbnail_url="https://example.com/thumbnails/test.png",
    )
    assert entry.id == 1
    assert entry.title == "Test Video"
    assert entry.video_url == "https://example.com/videos/test.webm"
    assert entry.thumbnail_url == "https://example.com/thumbnails/test.png"


def test_catalog_to_json():
    entries = [
        CatalogEntry(id=1, title="Video A", video_url="https://x.com/a.webm", thumbnail_url="https://x.com/a.png"),
        CatalogEntry(id=2, title="Video B", video_url="https://x.com/b.webm", thumbnail_url="https://x.com/b.png"),
    ]
    catalog = Catalog(videos=entries)
    result = json.loads(catalog.to_json())

    assert "videos" in result
    assert len(result["videos"]) == 2
    assert result["videos"][0]["id"] == 1
    assert result["videos"][1]["title"] == "Video B"


def test_build_catalog_creates_urls():
    videos = [
        {"id": 1, "title": "Test", "video_path": "/path/to/videos/test.webm", "thumbnail_path": "/path/to/thumbnails/test.png"},
    ]
    catalog = build_catalog(videos, "https://cdn.example.com", None)

    assert len(catalog.videos) == 1
    assert catalog.videos[0].video_url == "https://cdn.example.com/videos/test.webm"
    assert catalog.videos[0].thumbnail_url == "https://cdn.example.com/thumbnails/test.png"


def test_build_catalog_with_prefix():
    videos = [
        {"id": 1, "title": "Test", "video_path": "/path/to/videos/test.webm", "thumbnail_path": "/path/to/thumbnails/test.png"},
    ]
    catalog = build_catalog(videos, "https://cdn.example.com", "media")

    assert catalog.videos[0].video_url == "https://cdn.example.com/media/videos/test.webm"
    assert catalog.videos[0].thumbnail_url == "https://cdn.example.com/media/thumbnails/test.png"


def test_build_catalog_strips_trailing_slash():
    videos = [
        {"id": 1, "title": "Test", "video_path": "/path/to/videos/test.webm", "thumbnail_path": "/path/to/thumbnails/test.png"},
    ]
    catalog = build_catalog(videos, "https://cdn.example.com/", None)

    assert catalog.videos[0].video_url == "https://cdn.example.com/videos/test.webm"


def test_build_catalog_strips_prefix_slashes():
    videos = [
        {"id": 1, "title": "Test", "video_path": "/path/to/videos/test.webm", "thumbnail_path": "/path/to/thumbnails/test.png"},
    ]
    catalog = build_catalog(videos, "https://cdn.example.com", "/media/")

    assert catalog.videos[0].video_url == "https://cdn.example.com/media/videos/test.webm"


def test_build_catalog_sorts_by_title_then_id():
    videos = [
        {"id": 3, "title": "Zebra", "video_path": "/videos/z.webm", "thumbnail_path": "/thumbs/z.png"},
        {"id": 1, "title": "Alpha", "video_path": "/videos/a.webm", "thumbnail_path": "/thumbs/a.png"},
        {"id": 2, "title": "Alpha", "video_path": "/videos/a2.webm", "thumbnail_path": "/thumbs/a2.png"},
    ]
    catalog = build_catalog(videos, "https://x.com", None)

    assert catalog.videos[0].title == "Alpha"
    assert catalog.videos[0].id == 1  # Lower id comes first
    assert catalog.videos[1].title == "Alpha"
    assert catalog.videos[1].id == 2
    assert catalog.videos[2].title == "Zebra"


def test_build_catalog_case_insensitive_sort():
    videos = [
        {"id": 1, "title": "zebra", "video_path": "/videos/z.webm", "thumbnail_path": "/thumbs/z.png"},
        {"id": 2, "title": "Alpha", "video_path": "/videos/a.webm", "thumbnail_path": "/thumbs/a.png"},
    ]
    catalog = build_catalog(videos, "https://x.com", None)

    assert catalog.videos[0].title == "Alpha"
    assert catalog.videos[1].title == "zebra"


def test_write_catalog(tmp_path):
    entries = [
        CatalogEntry(id=1, title="Test", video_url="https://x.com/a.webm", thumbnail_url="https://x.com/a.png"),
    ]
    catalog = Catalog(videos=entries)
    output_path = tmp_path / "catalog.json"

    write_catalog(catalog, output_path)

    assert output_path.exists()
    content = json.loads(output_path.read_text())
    assert content["videos"][0]["title"] == "Test"


def test_write_catalog_creates_parent_dirs(tmp_path):
    entries = [
        CatalogEntry(id=1, title="Test", video_url="https://x.com/a.webm", thumbnail_url="https://x.com/a.png"),
    ]
    catalog = Catalog(videos=entries)
    output_path = tmp_path / "nested" / "dir" / "catalog.json"

    write_catalog(catalog, output_path)

    assert output_path.exists()
