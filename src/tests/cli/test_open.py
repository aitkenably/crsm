from __future__ import annotations

from unittest.mock import patch

from crsm.cli.app import app


def test_open_launches_file_browser_macos(runner, temp_db_path, tmp_path):
    """open command launches Finder on macOS."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    (library_path / "videos").mkdir()
    (library_path / "thumbnails").mkdir()

    with patch("crsm.cli.commands.open.platform.system", return_value="Darwin"), \
         patch("crsm.cli.commands.open.subprocess.Popen") as mock_popen:
        r = runner.invoke(app, ["--db", str(temp_db_path), "--library", str(library_path), "open"])

    assert r.exit_code == 0
    assert "Opened:" in r.stdout
    mock_popen.assert_called_once_with(["open", str(library_path)])


def test_open_launches_file_browser_linux(runner, temp_db_path, tmp_path):
    """open command launches xdg-open on Linux."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    (library_path / "videos").mkdir()
    (library_path / "thumbnails").mkdir()

    with patch("crsm.cli.commands.open.platform.system", return_value="Linux"), \
         patch("crsm.cli.commands.open.subprocess.Popen") as mock_popen:
        r = runner.invoke(app, ["--db", str(temp_db_path), "--library", str(library_path), "open"])

    assert r.exit_code == 0
    mock_popen.assert_called_once_with(["xdg-open", str(library_path)])


def test_open_launches_file_browser_windows(runner, temp_db_path, tmp_path):
    """open command launches explorer on Windows."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    (library_path / "videos").mkdir()
    (library_path / "thumbnails").mkdir()

    with patch("crsm.cli.commands.open.platform.system", return_value="Windows"), \
         patch("crsm.cli.commands.open.subprocess.Popen") as mock_popen:
        r = runner.invoke(app, ["--db", str(temp_db_path), "--library", str(library_path), "open"])

    assert r.exit_code == 0
    mock_popen.assert_called_once_with(["explorer", str(library_path)])


def test_open_unsupported_platform(runner, temp_db_path, tmp_path):
    """open command returns error on unsupported platform."""
    library_path = tmp_path / "library"
    library_path.mkdir()
    (library_path / "videos").mkdir()
    (library_path / "thumbnails").mkdir()

    with patch("crsm.cli.commands.open.platform.system", return_value="UnknownOS"):
        r = runner.invoke(app, ["--db", str(temp_db_path), "--library", str(library_path), "open"])

    assert r.exit_code == 2
    assert "Unsupported platform" in r.stdout
