from __future__ import annotations

import logging
from pathlib import Path


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

    def delete_video_files(self, video_filename: str, thumbnail_filename: str) -> list[str]:
        """
        Delete both video and thumbnail files.

        Returns a list of error messages for any failures.
        Missing files are not considered errors (just logged as warnings).
        """
        errors = []

        try:
            self.delete_video(video_filename)
        except OSError as e:
            error_msg = f"Failed to delete video file {video_filename}: {e}"
            errors.append(error_msg)
            logging.error(error_msg)

        try:
            self.delete_thumbnail(thumbnail_filename)
        except OSError as e:
            error_msg = f"Failed to delete thumbnail file {thumbnail_filename}: {e}"
            errors.append(error_msg)
            logging.error(error_msg)

        return errors
