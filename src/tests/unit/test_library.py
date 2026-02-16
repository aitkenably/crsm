from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crsm.library import (
    CrsmLibrary,
    SUPPORTED_VIDEO_EXTENSIONS,
    ThumbnailGenerationError,
)


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

        errors = library.delete_video_files("videos/test_video.webm", "thumbnails/test_video.png")

        assert errors == []
        assert not video_file.exists()
        assert not thumb_file.exists()

    def test_delete_video_files_missing_files(self, tmp_path):
        library = CrsmLibrary(tmp_path)

        errors = library.delete_video_files("videos/missing.webm", "thumbnails/missing.png")

        # Missing files should not produce errors, just warnings
        assert errors == []

    def test_delete_video_files_partial_success(self, library_with_files):
        library, video_file, thumb_file = library_with_files

        # Delete only the video file first
        video_file.unlink()

        errors = library.delete_video_files("videos/test_video.webm", "thumbnails/test_video.png")

        # No errors - missing video just logged as warning
        assert errors == []
        assert not thumb_file.exists()

    def test_delete_video_files_permission_error(self, library_with_files, monkeypatch):
        library, video_file, thumb_file = library_with_files

        def mock_unlink(self):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        errors = library.delete_video_files("videos/test_video.webm", "thumbnails/test_video.png")

        assert len(errors) == 2
        assert "video" in errors[0].lower()
        assert "thumbnail" in errors[1].lower()


class TestSupportedExtensions:
    def test_is_supported_extension_webm(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        assert library.is_supported_extension(Path("video.webm")) is True

    def test_is_supported_extension_mp4(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        assert library.is_supported_extension(Path("video.mp4")) is True

    def test_is_supported_extension_unsupported(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        assert library.is_supported_extension(Path("file.txt")) is False
        assert library.is_supported_extension(Path("file.pdf")) is False

    def test_is_supported_extension_case_insensitive(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        assert library.is_supported_extension(Path("video.MP4")) is True
        assert library.is_supported_extension(Path("video.WebM")) is True


class TestEnsureDirectories:
    def test_ensure_directories_creates_dirs(self, tmp_path):
        library_path = tmp_path / "library"
        library = CrsmLibrary(library_path)

        assert not library.videos_dir.exists()
        assert not library.thumbnails_dir.exists()

        library.ensure_directories()

        assert library.videos_dir.exists()
        assert library.thumbnails_dir.exists()

    def test_ensure_directories_idempotent(self, tmp_path):
        library_path = tmp_path / "library"
        library = CrsmLibrary(library_path)

        library.ensure_directories()
        library.ensure_directories()  # Should not raise

        assert library.videos_dir.exists()


class TestImportVideo:
    def test_import_video_move_success(self, tmp_path):
        # Setup
        library_path = tmp_path / "library"
        library = CrsmLibrary(library_path)
        source_file = tmp_path / "source_video.webm"
        source_file.write_text("fake video content")

        # Execute
        result = library.import_video(source_file, "dest_video.webm", move=True)

        # Verify
        assert result == library.videos_dir / "dest_video.webm"
        assert result.exists()
        assert not source_file.exists()  # Source was moved

    def test_import_video_copy_success(self, tmp_path):
        # Setup
        library_path = tmp_path / "library"
        library = CrsmLibrary(library_path)
        source_file = tmp_path / "source_video.webm"
        source_file.write_text("fake video content")

        # Execute
        result = library.import_video(source_file, "dest_video.webm", move=False)

        # Verify
        assert result == library.videos_dir / "dest_video.webm"
        assert result.exists()
        assert source_file.exists()  # Source was preserved

    def test_import_video_destination_exists_raises(self, tmp_path):
        # Setup
        library_path = tmp_path / "library"
        library = CrsmLibrary(library_path)
        library.ensure_directories()

        # Create existing file at destination
        existing = library.videos_dir / "existing.webm"
        existing.write_text("existing content")

        source_file = tmp_path / "source.webm"
        source_file.write_text("new content")

        # Execute & verify
        with pytest.raises(FileExistsError, match="Video already exists"):
            library.import_video(source_file, "existing.webm", move=True)

    def test_import_video_creates_videos_dir(self, tmp_path):
        library_path = tmp_path / "new_library"
        library = CrsmLibrary(library_path)

        source_file = tmp_path / "video.webm"
        source_file.write_text("content")

        assert not library.videos_dir.exists()

        library.import_video(source_file, "video.webm", move=True)

        assert library.videos_dir.exists()


class TestGenerateThumbnail:
    def test_generate_thumbnail_video_not_found(self, tmp_path):
        library = CrsmLibrary(tmp_path)
        library.ensure_directories()

        with pytest.raises(FileNotFoundError, match="Video file not found"):
            library.generate_thumbnail("nonexistent.webm", "thumb.png")

    def test_generate_thumbnail_ffmpeg_not_found(self, tmp_path):
        library_path = tmp_path / "library"
        library = CrsmLibrary(library_path)
        library.ensure_directories()

        # Create a video file
        video_path = library.videos_dir / "test.webm"
        video_path.write_text("fake video")

        # Mock subprocess.run to raise FileNotFoundError (ffmpeg not found)
        with patch("crsm.library.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("ffmpeg not found")

            with pytest.raises(ThumbnailGenerationError, match="ffmpeg not found"):
                library.generate_thumbnail("test.webm", "test.png")

    def test_generate_thumbnail_ffmpeg_fails(self, tmp_path):
        library_path = tmp_path / "library"
        library = CrsmLibrary(library_path)
        library.ensure_directories()

        # Create a video file
        video_path = library.videos_dir / "test.webm"
        video_path.write_text("fake video")

        # Mock subprocess.run to return failure
        with patch("crsm.library.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Invalid input"

            with pytest.raises(ThumbnailGenerationError, match="ffmpeg failed"):
                library.generate_thumbnail("test.webm", "test.png")
