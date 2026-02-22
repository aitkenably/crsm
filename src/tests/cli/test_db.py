from __future__ import annotations

from unittest.mock import patch, MagicMock

from crsm.cli.app import app


def test_db_missing_sqlite3(runner, temp_db_path, tmp_path):
    """db command returns error when sqlite3 is not in PATH."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    (library_path / "videos").mkdir()
    (library_path / "thumbnails").mkdir()

    with patch("shutil.which", return_value=None):
        r = runner.invoke(app, ["--db", str(temp_db_path), "--library", str(library_path), "db"])

    assert r.exit_code == 2
    assert "sqlite3 command not found" in r.stdout


def test_db_launches_sqlite3(runner, temp_db_path, tmp_path):
    """db command launches sqlite3 with the database path."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    (library_path / "videos").mkdir()
    (library_path / "thumbnails").mkdir()

    with patch("shutil.which", return_value="/usr/bin/sqlite3") as mock_which, \
         patch("subprocess.run") as mock_run:
        r = runner.invoke(app, ["--db", str(temp_db_path), "--library", str(library_path), "db"])

    assert r.exit_code == 0
    mock_which.assert_called_once_with("sqlite3")
    mock_run.assert_called_once_with(["/usr/bin/sqlite3", str(temp_db_path)])
