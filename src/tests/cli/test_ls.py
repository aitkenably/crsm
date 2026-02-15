from __future__ import annotations

from crsm.cli.app import app


def test_ls(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls"])
    assert r.exit_code == 0
    assert "Chill Beats" in r.stdout


def test_ls_with_search(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--search", "Zen"])
    assert r.exit_code == 0
    assert "Zen Garden" in r.stdout
    assert "Chill Beats" not in r.stdout


def test_ls_with_offset(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--offset", "2"])
    assert r.exit_code == 0
    # With offset=2, should skip first 2 rows (Chill Beats, Study Music 2)
    assert "Chill Beats" not in r.stdout
    assert "Study Music 2" not in r.stdout
    assert "Alpha Waves" in r.stdout
    assert "Zen Garden" in r.stdout


def test_ls_with_sort_title(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--sort", "title"])
    assert r.exit_code == 0
    # Alpha Waves should be first when sorted by title ASC
    output_lines = r.stdout.split("\n")
    alpha_pos = next(i for i, line in enumerate(output_lines) if "Alpha Waves" in line)
    zen_pos = next(i for i, line in enumerate(output_lines) if "Zen Garden" in line)
    assert alpha_pos < zen_pos


def test_ls_with_desc(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--sort", "title", "--desc"])
    assert r.exit_code == 0
    # Zen Garden should be first when sorted by title DESC
    output_lines = r.stdout.split("\n")
    alpha_pos = next(i for i, line in enumerate(output_lines) if "Alpha Waves" in line)
    zen_pos = next(i for i, line in enumerate(output_lines) if "Zen Garden" in line)
    assert zen_pos < alpha_pos


def test_ls_with_fields_id_only(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--fields", "id"])
    assert r.exit_code == 0
    # Should not show title column header or values
    assert "title" not in r.stdout.lower().split("\n")[0]  # header line


def test_ls_with_fields_title_only(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--fields", "title"])
    assert r.exit_code == 0
    assert "Chill Beats" in r.stdout


def test_ls_invalid_sort_exits(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--sort", "invalid"])
    assert r.exit_code == 1
    assert "Invalid sort value" in r.stdout


def test_ls_invalid_fields_exits(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--fields", "foo"])
    assert r.exit_code == 1
    assert "Invalid field" in r.stdout


def test_db_flag_missing_directory_exits_with_error(runner, tmp_path):
    missing_db = tmp_path / "nonexistent" / "subdir" / "db.sqlite"
    r = runner.invoke(app, ["--db", str(missing_db), "ls"])
    assert r.exit_code == 1
    assert "Database directory does not exist" in r.stdout


def test_config_flag_missing_file_exits_with_error(runner, tmp_path):
    missing_config = tmp_path / "nonexistent" / "config.toml"
    r = runner.invoke(app, ["--config", str(missing_config), "ls"])
    assert r.exit_code == 1
    assert "Config file does not exist" in r.stdout
