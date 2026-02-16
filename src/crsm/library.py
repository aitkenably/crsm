from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

SUPPORTED_VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v"
})


class ThumbnailGenerationError(Exception):
    """Raised when thumbnail generation fails."""


class CrsmLibrary:
    """Manages the video library filesystem structure."""

    def __init__(self, library_path: Path):
        self.library_path = library_path
        self.videos_dir = library_path / "videos"
        self.thumbnails_dir = library_path / "thumbnails"

    def get_video_path(self, video_filename: str) -> Path:
        """Get the full path to a video file."""
        return self.videos_dir / video_filename

    def get_thumbnail_path(self, thumbnail_filename: str) -> Path:
        """Get the full path to a thumbnail file."""
        return self.thumbnails_dir / thumbnail_filename

    def get_full_path(self, relative_path: str) -> Path:
        """Get the full path from a library-relative path."""
        return self.library_path / relative_path

    def get_relative_video_path(self, video_filename: str) -> str:
        """Get the relative path for a video file (e.g., 'videos/filename.webm')."""
        return f"videos/{video_filename}"

    def get_relative_thumbnail_path(self, thumb_filename: str) -> str:
        """Get the relative path for a thumbnail file (e.g., 'thumbnails/filename.png')."""
        return f"thumbnails/{thumb_filename}"

    def video_exists(self, video_filename: str) -> bool:
        """Check if a video file exists."""
        return self.get_video_path(video_filename).exists()

    def thumbnail_exists(self, thumbnail_filename: str) -> bool:
        """Check if a thumbnail file exists."""
        return self.get_thumbnail_path(thumbnail_filename).exists()

    def delete_video(self, video_filename: str) -> bool:
        """
        Delete a video file.

        Returns True if file was deleted, False if it didn't exist.
        Raises OSError on deletion failure.
        """
        video_path = self.get_video_path(video_filename)
        if video_path.exists():
            video_path.unlink()
            logging.info(f"Deleted video file: {video_path}")
            return True
        else:
            logging.warning(f"Video file not found: {video_path}")
            return False

    def delete_thumbnail(self, thumbnail_filename: str) -> bool:
        """
        Delete a thumbnail file.

        Returns True if file was deleted, False if it didn't exist.
        Raises OSError on deletion failure.
        """
        thumbnail_path = self.get_thumbnail_path(thumbnail_filename)
        if thumbnail_path.exists():
            thumbnail_path.unlink()
            logging.info(f"Deleted thumbnail file: {thumbnail_path}")
            return True
        else:
            logging.warning(f"Thumbnail file not found: {thumbnail_path}")
            return False

    def delete_video_files(self, video_path: str, thumbnail_path: str) -> list[str]:
        """
        Delete both video and thumbnail files.

        Args:
            video_path: Relative path to video (e.g., 'videos/filename.webm')
            thumbnail_path: Relative path to thumbnail (e.g., 'thumbnails/filename.png')

        Returns a list of error messages for any failures.
        Missing files are not considered errors (just logged as warnings).
        """
        errors = []

        try:
            self.delete_file(video_path)
        except OSError as e:
            error_msg = f"Failed to delete video file {video_path}: {e}"
            errors.append(error_msg)
            logging.error(error_msg)

        try:
            self.delete_file(thumbnail_path)
        except OSError as e:
            error_msg = f"Failed to delete thumbnail file {thumbnail_path}: {e}"
            errors.append(error_msg)
            logging.error(error_msg)

        return errors

    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file by its relative path.

        Returns True if file was deleted, False if it didn't exist.
        Raises OSError on deletion failure.
        """
        full_path = self.get_full_path(relative_path)
        if full_path.exists():
            full_path.unlink()
            logging.info(f"Deleted file: {full_path}")
            return True
        else:
            logging.warning(f"File not found: {full_path}")
            return False

    def ensure_directories(self) -> None:
        """Create videos and thumbnails directories if they don't exist."""
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    def is_supported_extension(self, path: Path) -> bool:
        """Check if a file has a supported video extension."""
        return path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS

    def import_video(self, source: Path, dest_filename: str, move: bool = True) -> Path:
        """
        Import a video file into the library.

        Args:
            source: Path to the source video file
            dest_filename: Filename to use in the library (without path)
            move: If True, move the file; if False, copy it

        Returns:
            Path to the imported video file

        Raises:
            FileExistsError: If destination already exists
            OSError: If import fails
        """
        self.ensure_directories()
        dest_path = self.videos_dir / dest_filename

        if dest_path.exists():
            raise FileExistsError(f"Video already exists: {dest_path}")

        if move:
            shutil.move(str(source), str(dest_path))
            logging.info(f"Moved video from {source} to {dest_path}")
        else:
            shutil.copy2(str(source), str(dest_path))
            logging.info(f"Copied video from {source} to {dest_path}")

        return dest_path

    def generate_thumbnail(
        self, video_filename: str, thumb_filename: str, timestamp: int = 60
    ) -> Path:
        """
        Generate a thumbnail from a video file using ffmpeg.

        Args:
            video_filename: Name of the video file in the library
            thumb_filename: Name for the thumbnail file
            timestamp: Time in seconds to capture the frame (default 60)

        Returns:
            Path to the generated thumbnail

        Raises:
            ThumbnailGenerationError: If thumbnail generation fails
            FileNotFoundError: If video file doesn't exist
        """
        self.ensure_directories()
        video_path = self.videos_dir / video_filename
        thumb_path = self.thumbnails_dir / thumb_filename

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(thumb_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                # Try with timestamp 0 if the specified timestamp is beyond video length
                if timestamp > 0:
                    logging.warning(
                        f"Thumbnail at {timestamp}s failed, trying at 0s"
                    )
                    cmd[3] = "0"
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                if result.returncode != 0:
                    raise ThumbnailGenerationError(
                        f"ffmpeg failed: {result.stderr}"
                    )
        except FileNotFoundError:
            raise ThumbnailGenerationError(
                "ffmpeg not found. Please install ffmpeg."
            )

        if not thumb_path.exists():
            raise ThumbnailGenerationError(
                f"Thumbnail was not created: {thumb_path}"
            )

        logging.info(f"Generated thumbnail: {thumb_path}")
        return thumb_path
