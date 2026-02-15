from __future__ import annotations

import pytest

from crsm.repo import CrsmRepo


def test_list_video(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(limit=10)
    assert len(rows) == 4
    assert rows[0]["title"] == "Chill Beats"  # id ASC by default


def test_list_video_with_offset(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(limit=10, offset=2)
    assert len(rows) == 2
    assert rows[0]["title"] == "Alpha Waves"  # 3rd item (id=3)


def test_list_video_with_search(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(search="Zen")
    assert len(rows) == 1
    assert rows[0]["title"] == "Zen Garden"


def test_list_video_search_partial_match(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(search="Music")
    assert len(rows) == 1
    assert rows[0]["title"] == "Study Music 2"


def test_list_video_sort_by_title_asc(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(sort_by="title", descending=False)
    titles = [r["title"] for r in rows]
    assert titles == ["Alpha Waves", "Chill Beats", "Study Music 2", "Zen Garden"]


def test_list_video_sort_by_title_desc(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(sort_by="title", descending=True)
    titles = [r["title"] for r in rows]
    assert titles == ["Zen Garden", "Study Music 2", "Chill Beats", "Alpha Waves"]


def test_list_video_sort_by_id_asc(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(sort_by="id", descending=False)
    ids = [r["id"] for r in rows]
    assert ids == [1, 2, 3, 4]


def test_list_video_sort_by_id_desc(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    rows = repo.list_video(sort_by="id", descending=True)
    ids = [r["id"] for r in rows]
    assert ids == [4, 3, 2, 1]


def test_list_video_invalid_sort_raises(seeded_db_path):
    repo = CrsmRepo(seeded_db_path)

    with pytest.raises(ValueError, match="Invalid sort_by value"):
        repo.list_video(sort_by="invalid")
