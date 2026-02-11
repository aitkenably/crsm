from __future__ import annotations

from crsm.cli.app import app

def test_end_to_end_flow(runner, temp_db_path):
    r = runner.invoke(app, ["--db", str(temp_db_path), "add", "main", "--name", "alpha"])
    assert r.exit_code == 0

    r = runner.invoke(app, ["--db", str(temp_db_path), "add", "main", "--name", "beta"])
    assert r.exit_code == 0

    r = runner.invoke(app, ["--db", str(temp_db_path), "ls"])
    assert r.exit_code == 0
    assert "alpha" in r.stdout
    assert "beta" in r.stdout
