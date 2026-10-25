from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


class DatabaseMissingError(RuntimeError):
    """A previously-initialised project lost its database path."""


def _portable_base() -> Path:
    """Use the application folder as the portable project folder."""
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            parts = executable.parts
            if ".app" in parts:
                app_index = len(parts) - 1 - parts[::-1].index(".app")
                return Path(*parts[:app_index + 1]).parent
        return executable.parent
    return Path(__file__).resolve().parents[2]


BASE_DIR = _portable_base()
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "grainprint.duckdb"
DB_URL = f"duckdb:///{DB_PATH}"
SEED_DB_PATH = Path(__file__).with_name("data") / "grainprint.duckdb"
PROJECT_MANIFEST = DATA_DIR / "grainprint-project.json"


def _write_manifest() -> None:
    PROJECT_MANIFEST.write_text(json.dumps({"database": DB_PATH.name, "format": 1}, ensure_ascii=False), encoding="utf-8")


def ensure_database() -> None:
    """Create a seed only for a genuine first launch.

    Once a folder has held a GrainPrint project, a missing DB is an error—not
    a reason to silently start an empty/seed database and make data appear lost.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        if not PROJECT_MANIFEST.exists():
            _write_manifest()  # adopt v0.4.0 projects without moving their data
        return
    if PROJECT_MANIFEST.exists():
        raise DatabaseMissingError(
            f"未找到原数据库：{DB_PATH}\n"
            "为避免把数据丢失伪装成新项目，软件不会自动新建数据库。"
        )
    if SEED_DB_PATH.exists():
        shutil.copy2(SEED_DB_PATH, DB_PATH)
    _write_manifest()


ensure_database()
