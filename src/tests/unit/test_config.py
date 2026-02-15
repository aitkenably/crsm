from __future__ import annotations

from pathlib import Path

import pytest

from crsm.config import (
    AppConfig,
    load_config,
    DEFAULT_CONFIG_PATH,
    DEFAULT_DB_PATH,
    DEFAULT_REPO_PATH,
)


class TestAppConfig:
    def test_appconfig_is_frozen(self):
        config = AppConfig(db_path=Path("/db"), repo_path=Path("/repo"))
        with pytest.raises(AttributeError):
            config.db_path = Path("/new")

    def test_appconfig_stores_paths(self):
        db = Path("/custom/db.sqlite")
        repo = Path("/custom/library")
        config = AppConfig(db_path=db, repo_path=repo)
        assert config.db_path == db
        assert config.repo_path == repo


class TestLoadConfigDefaults:
    def test_returns_default_db_path_when_no_config_file(self, tmp_path, monkeypatch):
        # Point to non-existent config file
        fake_config = tmp_path / "nonexistent" / "config.toml"
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", tmp_path / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_REPO_PATH", tmp_path / "library")

        config = load_config(fake_config)

        assert config.db_path == tmp_path / "default.db"

    def test_returns_default_repo_path_when_no_config_file(self, tmp_path, monkeypatch):
        fake_config = tmp_path / "nonexistent" / "config.toml"
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", tmp_path / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_REPO_PATH", tmp_path / "library")

        config = load_config(fake_config)

        assert config.repo_path == tmp_path / "library"

    def test_uses_default_config_path_when_none_provided(self, monkeypatch, tmp_path):
        # Set defaults to tmp_path to avoid touching real filesystem
        monkeypatch.setattr("crsm.config.DEFAULT_CONFIG_PATH", tmp_path / "config.toml")
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", tmp_path / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_REPO_PATH", tmp_path / "library")

        config = load_config(None)

        assert config.db_path == tmp_path / "default.db"
        assert config.repo_path == tmp_path / "library"


class TestLoadConfigFromFile:
    def test_reads_db_path_from_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("crsm.config.DEFAULT_REPO_PATH", tmp_path / "library")
        config_file = tmp_path / "config.toml"
        custom_db = tmp_path / "custom" / "db.sqlite"
        config_file.write_text(f'[db]\npath = "{custom_db}"\n')

        config = load_config(config_file)

        assert config.db_path == custom_db

    def test_reads_repo_path_from_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", tmp_path / "default.db")
        config_file = tmp_path / "config.toml"
        custom_repo = tmp_path / "custom" / "library"
        config_file.write_text(f'[repo]\npath = "{custom_repo}"\n')

        config = load_config(config_file)

        assert config.repo_path == custom_repo

    def test_reads_both_paths_from_config(self, tmp_path):
        config_file = tmp_path / "config.toml"
        custom_db = tmp_path / "opt" / "crsm" / "crsm.db"
        custom_repo = tmp_path / "opt" / "crsm" / "library"
        config_file.write_text(
            f'[db]\npath = "{custom_db}"\n\n'
            f'[repo]\npath = "{custom_repo}"\n'
        )

        config = load_config(config_file)

        assert config.db_path == custom_db
        assert config.repo_path == custom_repo

    def test_uses_default_db_when_not_in_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", tmp_path / "default.db")
        config_file = tmp_path / "config.toml"
        custom_repo = tmp_path / "custom" / "library"
        config_file.write_text(f'[repo]\npath = "{custom_repo}"\n')

        config = load_config(config_file)

        assert config.db_path == tmp_path / "default.db"

    def test_uses_default_repo_when_not_in_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("crsm.config.DEFAULT_REPO_PATH", tmp_path / "library")
        config_file = tmp_path / "config.toml"
        custom_db = tmp_path / "custom" / "db.sqlite"
        config_file.write_text(f'[db]\npath = "{custom_db}"\n')

        config = load_config(config_file)

        assert config.repo_path == tmp_path / "library"

    def test_handles_empty_config_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("crsm.config.DEFAULT_DB_PATH", tmp_path / "default.db")
        monkeypatch.setattr("crsm.config.DEFAULT_REPO_PATH", tmp_path / "library")
        config_file = tmp_path / "config.toml"
        config_file.write_text("")

        config = load_config(config_file)

        assert config.db_path == tmp_path / "default.db"
        assert config.repo_path == tmp_path / "library"


class TestLoadConfigDirectoryCreation:
    def test_creates_db_parent_directory(self, tmp_path):
        config_file = tmp_path / "config.toml"
        db_path = tmp_path / "subdir" / "nested" / "db.sqlite"
        config_file.write_text(f'[db]\npath = "{db_path}"\n')

        load_config(config_file)

        assert db_path.parent.exists()

    def test_creates_repo_directory(self, tmp_path):
        config_file = tmp_path / "config.toml"
        repo_path = tmp_path / "subdir" / "nested" / "library"
        config_file.write_text(f'[repo]\npath = "{repo_path}"\n')

        load_config(config_file)

        assert repo_path.exists()

    def test_creates_config_parent_directory(self, tmp_path):
        config_file = tmp_path / "subdir" / "config.toml"
        # Config file doesn't exist, but parent should be created

        load_config(config_file)

        assert config_file.parent.exists()


class TestDefaultPaths:
    def test_default_config_path_uses_xdg_config_home(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        # Need to reload module to pick up env change
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

    def test_default_repo_path_uses_xdg_data_home(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")
        import importlib
        import crsm.config
        importlib.reload(crsm.config)

        assert crsm.config.DEFAULT_REPO_PATH == Path("/custom/data/crsm/library")
