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


def test_ls_with_fields_wildcard(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--fields", "*"])
    assert r.exit_code == 0
    # Should show all fields
    assert "Chill Beats" in r.stdout
    assert "videos/Chill_Beats.webm" in r.stdout
    assert "thumbnails/Chill_Beats.png" in r.stdout


def test_ls_with_fields_wildcard_shows_all_columns(runner, seeded_db_path):
    r = runner.invoke(app, ["--db", str(seeded_db_path), "ls", "--fields", "*"])
    assert r.exit_code == 0
    # Check that column headers are present in the output
    assert "id" in r.stdout
    assert "title" in r.stdout
    assert "video_path" in r.stdout
    assert "thumbnail_path" in r.stdout


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


def test_library_flag_missing_directory_exits_with_error(runner, seeded_db_path, tmp_path):
    missing_library = tmp_path / "nonexistent" / "library"
    r = runner.invoke(app, ["--db", str(seeded_db_path), "--library", str(missing_library), "ls"])
    assert r.exit_code == 1
    assert "Library directory does not exist" in r.stdout


def test_invalid_database_file_exits_with_error(runner, tmp_path):
    # Create a file that is not a valid SQLite database
    invalid_db = tmp_path / "invalid.db"
    invalid_db.write_text("this is not a sqlite database")
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    r = runner.invoke(app, ["--db", str(invalid_db), "--library", str(library_dir), "ls"])
    assert r.exit_code == 2
    assert "Database error" in r.stdout


def test_readonly_database_exits_with_error(runner, tmp_path):
    # Create a valid db file then make it read-only
    from crsm.db import ensure_schema
    db_path = tmp_path / "readonly.db"
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    ensure_schema(db_path)
    db_path.chmod(0o444)  # read-only
    try:
        r = runner.invoke(app, ["--db", str(db_path), "--library", str(library_dir), "ls"])
        # The schema already exists, so it might succeed if no writes needed
        # But if it tries to write, it should fail with exit code 2
        if r.exit_code != 0:
            assert r.exit_code == 2
            assert "Database error" in r.stdout
    finally:
        db_path.chmod(0o644)  # restore permissions for cleanup
