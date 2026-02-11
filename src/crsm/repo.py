from __future__ import annotations

from pathlib import Path
from typing import Iterable
from crsm.db import get_connection

class CrsmRepo:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def add_item(self, name: str) -> int:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("INSERT INTO items(name) VALUES (?)", (name,))
            return int(cur.lastrowid)

    def list_items(self, limit: int = 50):
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id, name, created_at FROM items ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()

    def remove_item(self, item_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cur.rowcount > 0
