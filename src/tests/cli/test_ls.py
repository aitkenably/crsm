from __future__ import annotations

from crsm.cli.app import app  # the Typer app object

def test_ls(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls"])
    assert r.exit_code == 0
    assert "Chill Beats" in r.stdout
