from __future__ import annotations

from crsm.repo import CrsmRepo

def test_list_video(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(limit=10)
    assert len(rows) == 2
    assert rows[0]["title"] == "Study Music 2"
