from __future__ import annotations

from crsm.repo import CrsmRepo

def test_add_and_list_items(temp_db_path):
    repo = CrsmRepo(temp_db_path)

    new_id = repo.add_item("hello")
    assert isinstance(new_id, int)

    rows = repo.list_items(limit=10)
    assert len(rows) == 1
    assert rows[0]["id"] == new_id
    assert rows[0]["name"] == "hello"

def test_remove_item(temp_db_path):
    repo = CrsmRepo(temp_db_path)
    item_id = repo.add_item("to-delete")

    assert repo.remove_item(item_id) is True
    assert repo.remove_item(item_id) is False
