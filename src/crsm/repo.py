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

    def list_video(self, limit: int = 50):
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id, title FROM videos ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()

    def remove_video(self, video_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            return cur.rowcount > 0
