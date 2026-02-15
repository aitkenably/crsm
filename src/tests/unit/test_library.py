from __future__ import annotations

from pathlib import Path

import pytest

from crsm.library import CrsmLibrary


@pytest.fixture()
def library_with_files(tmp_path: Path) -> tuple[CrsmLibrary, Path, Path]:
    """Create a library with actual video and thumbnail files."""
    library_path = tmp_path / "library"
    videos_dir = library_path / "videos"
    thumbnails_dir = library_path / "thumbnails"
    videos_dir.mkdir(parents=True)
    thumbnails_dir.mkdir(parents=True)

    video_file = videos_dir / "test_video.webm"
    thumb_file = thumbnails_dir / "test_video.png"
    video_file.write_text("fake video content")
    thumb_file.write_text("fake thumbnail content")

    library = CrsmLibrary(library_path)
    return library, video_file, thumb_file


class TestCrsmLibraryPaths:
    def test_get_video_path(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        path = library.get_video_path("my_video.webm")
        assert path == tmp_path / "videos" / "my_video.webm"

    def test_get_thumbnail_path(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        path = library.get_thumbnail_path("my_thumb.png")
        assert path == tmp_path / "thumbnails" / "my_thumb.png"


class TestCrsmLibraryExists:
    def test_video_exists_true(self, library_with_files):
        library, video_file, _ = library_with_files
        assert library.video_exists("test_video.webm") is True

    def test_video_exists_false(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        assert library.video_exists("nonexistent.webm") is False

    def test_thumbnail_exists_true(self, library_with_files):
        library, _, thumb_file = library_with_files
        assert library.thumbnail_exists("test_video.png") is True

    def test_thumbnail_exists_false(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        assert library.thumbnail_exists("nonexistent.png") is False


class TestCrsmLibraryDeleteVideo:
    def test_delete_video_success(self, library_with_files):
        library, video_file, _ = library_with_files
        assert video_file.exists()

        result = library.delete_video("test_video.webm")

        assert result is True
        assert not video_file.exists()

    def test_delete_video_not_found(self, tmp_path):
        library = CrsmLibrary(tmp_path)

        result = library.delete_video("nonexistent.webm")

        assert result is False


class TestCrsmLibraryDeleteThumbnail:
    def test_delete_thumbnail_success(self, library_with_files):
        library, _, thumb_file = library_with_files
        assert thumb_file.exists()

        result = library.delete_thumbnail("test_video.png")

        assert result is True
        assert not thumb_file.exists()

    def test_delete_thumbnail_not_found(self, tmp_path):
        library = CrsmLibrary(tmp_path)

        result = library.delete_thumbnail("nonexistent.png")

        assert result is False


class TestCrsmLibraryDeleteVideoFiles:
    def test_delete_video_files_success(self, library_with_files):
        library, video_file, thumb_file = library_with_files
        assert video_file.exists()
        assert thumb_file.exists()

        errors = library.delete_video_files("test_video.webm", "test_video.png")

        assert errors == []
        assert not video_file.exists()
        assert not thumb_file.exists()

    def test_delete_video_files_missing_files(self, tmp_path):
        library = CrsmLibrary(tmp_path)

        errors = library.delete_video_files("missing.webm", "missing.png")

        # Missing files should not produce errors, just warnings
        assert errors == []

    def test_delete_video_files_partial_success(self, library_with_files):
        library, video_file, thumb_file = library_with_files

        # Delete only the video file first
        video_file.unlink()

        errors = library.delete_video_files("test_video.webm", "test_video.png")

        # No errors - missing video just logged as warning
        assert errors == []
        assert not thumb_file.exists()

    def test_delete_video_files_permission_error(self, library_with_files, monkeypatch):
        library, video_file, thumb_file = library_with_files

        def mock_unlink(self):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        errors = library.delete_video_files("test_video.webm", "test_video.png")

        assert len(errors) == 2
        assert "video" in errors[0].lower()
        assert "thumbnail" in errors[1].lower()
