from __future__ import annotations

from pathlib import Path

import pytest

from crsm.config import (
    AppConfig,
    ConfigError,
    load_config,
    DEFAULT_CONFIG_PATH,
    DEFAULT_DB_PATH,
    DEFAULT_LIBRARY_PATH,
)


class TestAppConfig:
    def test_appconfig_is_frozen(self):
        config = AppConfig(db_path=Path("/db"), library_path=Path("/repo"))
        with pytest.raises(AttributeError):
            config.db_path = Path("/new")

    def test_appconfig_stores_paths(self):
        db = Path("/custom/db.sqlite")
        repo = Path("/custom/library")
        config = AppConfig(db_path=db, library_path=repo)
        assert config.db_path == db
        assert config.library_path == repo


class TestLoadConfigDefaults:
    def test_returns_default_db_path_when_no_config_file(self, tmp_path, monkeypatch):
        fake_config = tmp_path / "nonexistent" / "config.toml"
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)

        config = load_config(fake_config)

        assert config.db_path == db_parent / "default.db"

    def test_returns_default_library_path_when_no_config_file(self, tmp_path, monkeypatch):
        fake_config = tmp_path / "nonexistent" / "config.toml"
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)

        config = load_config(fake_config)

        assert config.library_path == repo_dir

    def test_uses_default_config_path_when_none_provided(self, monkeypatch, tmp_path):
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_CONFIG_PATH", tmp_path / "config.toml")
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)

        config = load_config(None)

        assert config.db_path == db_parent / "default.db"
        assert config.library_path == repo_dir


class TestLoadConfigFromFile:
    def test_reads_db_path_from_config(self, tmp_path, monkeypatch):
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)
        config_file = tmp_path / "config.toml"
        custom_db_parent = tmp_path / "custom"
        custom_db_parent.mkdir()
        custom_db = custom_db_parent / "db.sqlite"
        config_file.write_text(f'[db]\npath = "{custom_db}"\n')

        config = load_config(config_file)

        assert config.db_path == custom_db

    def test_reads_library_path_from_config(self, tmp_path, monkeypatch):
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        config_file = tmp_path / "config.toml"
        custom_repo = tmp_path / "custom" / "library"
        custom_repo.mkdir(parents=True)
        config_file.write_text(f'[library]\npath = "{custom_repo}"\n')

        config = load_config(config_file)

        assert config.library_path == custom_repo

    def test_reads_both_paths_from_config(self, tmp_path):
        config_file = tmp_path / "config.toml"
        custom_db_parent = tmp_path / "opt" / "crsm"
        custom_db_parent.mkdir(parents=True)
        custom_db = custom_db_parent / "crsm.db"
        custom_repo = tmp_path / "opt" / "crsm" / "library"
        custom_repo.mkdir(parents=True)
        config_file.write_text(
            f'[db]\npath = "{custom_db}"\n\n'
            f'[library]\npath = "{custom_repo}"\n'
        )

        config = load_config(config_file)

        assert config.db_path == custom_db
        assert config.library_path == custom_repo

    def test_uses_default_db_when_not_in_config(self, tmp_path, monkeypatch):
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        config_file = tmp_path / "config.toml"
        custom_repo = tmp_path / "custom" / "library"
        custom_repo.mkdir(parents=True)
        config_file.write_text(f'[library]\npath = "{custom_repo}"\n')

        config = load_config(config_file)

        assert config.db_path == db_parent / "default.db"

    def test_uses_default_library_when_not_in_config(self, tmp_path, monkeypatch):
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)
        config_file = tmp_path / "config.toml"
        custom_db_parent = tmp_path / "custom"
        custom_db_parent.mkdir()
        custom_db = custom_db_parent / "db.sqlite"
        config_file.write_text(f'[db]\npath = "{custom_db}"\n')

        config = load_config(config_file)

        assert config.library_path == repo_dir

    def test_handles_empty_config_file(self, tmp_path, monkeypatch):
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        config = load_config(config_file)

        assert config.db_path == db_parent / "default.db"
        assert config.library_path == repo_dir


class TestLoadConfigMissingDirectories:
    def test_raises_when_db_parent_directory_missing(self, tmp_path, monkeypatch):
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)
        config_file = tmp_path / "config.toml"
        missing_db = tmp_path / "nonexistent" / "db.sqlite"
        config_file.write_text(f'[db]\npath = "{missing_db}"\n')

        with pytest.raises(ConfigError, match="Database directory does not exist"):
            load_config(config_file)

    def test_raises_when_library_directory_missing(self, tmp_path, monkeypatch):
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        config_file = tmp_path / "config.toml"
        missing_repo = tmp_path / "nonexistent" / "library"
        config_file.write_text(f'[library]\npath = "{missing_repo}"\n')

        with pytest.raises(ConfigError, match="Library directory does not exist"):
            load_config(config_file)

    def test_raises_when_default_db_parent_missing(self, tmp_path, monkeypatch):
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", tmp_path / "missing" / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        with pytest.raises(ConfigError, match="Database directory does not exist"):
            load_config(config_file)

    def test_raises_when_default_library_missing(self, tmp_path, monkeypatch):
        db_parent = tmp_path / "db"
        db_parent.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", db_parent / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", tmp_path / "missing" / "library")
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        with pytest.raises(ConfigError, match="Library directory does not exist"):
            load_config(config_file)

    def test_error_message_includes_path(self, tmp_path, monkeypatch):
        repo_dir = tmp_path / "library"
        repo_dir.mkdir()
        monkeypatch.setattr("crsm.config.DEFAULT_LIBRARY_PATH", repo_dir)
        config_file = tmp_path / "config.toml"
        missing_path = tmp_path / "some" / "missing" / "path"
        config_file.write_text(f'[db]\npath = "{missing_path / "db.sqlite"}"\n')

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)

        assert str(missing_path) in str(exc_info.value)


class TestDefaultPaths:
    def test_default_config_path_uses_xdg_config_home(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        import importlib
        import crsm.config
        importlib.reload(crsm.config)

        assert crsm.config.DEFAULT_CONFIG_PATH == Path("/custom/config/crsm/config.toml")

    def test_default_db_path_uses_xdg_state_home(self, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", "/custom/state")
        import importlib
        import crsm.config
        importlib.reload(crsm.config)

        assert crsm.config.DEFAULT_DB_PATH == Path("/custom/state/crsm/crsm.db")

    def test_default_library_path_uses_xdg_data_home(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")
        import importlib
        import crsm.config
        importlib.reload(crsm.config)

        assert crsm.config.DEFAULT_LIBRARY_PATH == Path("/custom/data/crsm/library")
