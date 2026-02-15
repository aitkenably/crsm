from __future__ import annotations

from pathlib import Path
from typing import Iterable
from crsm.db import get_connection

class CrsmRepo:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def add_video(self, title: str) -> int:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("INSERT INTO videos(title) VALUES (?)", (title,))
            return int(cur.lastrowid)

    def list_video(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        sort_by: str = "id",
        descending: bool = False,
    ) -> list:
        if sort_by not in ("id", "title"):
            raise ValueError(f"Invalid sort_by value: {sort_by}")

        query = "SELECT id, title FROM videos"
        params: list = []

        if search:
            query += " WHERE title LIKE ?"
            params.append(f"%{search}%")

        direction = "DESC" if descending else "ASC"
        query += f" ORDER BY {sort_by} {direction}"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_connection(self.db_path) as conn:
            cur = conn.execute(query, params)
            return cur.fetchall()

    def get_video_by_id(self, video_id: int):
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT id, title FROM videos WHERE id = ?", (video_id,))
            return cur.fetchone()

    def get_videos_by_title(self, title: str) -> list:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("SELECT id, title FROM videos WHERE title = ?", (title,))
            return cur.fetchall()

    def remove_video(self, video_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            return cur.rowcount > 0
