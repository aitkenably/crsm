# 🧰 CRSM – Command Line Tool #

crsm is a Python-based command line application built with modern CLI and 
packaging practices. It provides a structured command interface (ls, add, rm, live) 
backed by a local SQLite database and TOML configuration.

## 🏗️ Technology Stack ##

🐍 **Python (3.11+)**

Core language used for:
* CLI command definitions
* Database interaction
* Configuration loading
* Logging and utilities

Project uses modern Python features:
* Type hints
* pathlib
* dataclasses
* tomllib (built-in TOML parser)

## ⚙️ Typer (CLI Framework) ##

The command-line interface is built using **Typer**.

* Commands are defined as typed Python functions
* Automatic help text generation
* Shell completion support
* Clean subcommand structure

* Example command structure:

```bash
crsm ls
crsm add ...
crsm rm ...
crsm live
```
Each command is implemented as a standalone function and registered on the root Typer app.

## 🗄️ SQLite (Embedded Database) ##

* Persistent state is stored in a local SQLite database file.
* Accessed via Python’s built-in sqlite3
* Schema created automatically on first run
* WAL mode enabled for safer concurrent access
* Row factory configured for dict-like row access

Database access is isolated in a repository layer (repo.py) to separate business 
logic from CLI concerns.

# 📄 TOML Configuration #
Configuration is stored in a TOML file:
* Loaded via tomllib
* Supports user overrides via --config
* Defaults to XDG-style config/state paths
* Allows database path customization
* 
Example:
```toml
[db]
path = "/home/user/.local/state/crsm/crsm.db"
```

## 🧪 Testing (pytest) ##

Testing is structured in layers:

* Unit tests: repository and config logic
* CLI tests: Typer commands via CliRunner
* Integration tests: end-to-end flows

* Tests use temporary SQLite databases to ensure isolation and reproducibility.

## 🧩 Architecture Overview ##

```bash 
crsm/
  cli/           # Typer application + command wiring
  commands/      # ls, add, rm, live
  repo.py        # database access layer
  db.py          # schema + connection management
  config.py      # TOML config loading
  logging_utils.py
```

Design principles:
* CLI layer is thin
* Business logic is testable and importable
* Database access is centralized
* Configuration is deterministic and overridable
* Commands are explicit (no dynamic magic)

## 🎯 Design Goals ##
* Installable via pip install -e .
* Predictable CLI UX
* Minimal runtime dependencies
* Testable architecture