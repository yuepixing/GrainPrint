from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _portable_base() -> Path:
    """Return the directory that should hold the app-local data folder.

    Development uses the repository root. Packaged apps use the directory
    containing the executable (Windows/Linux) or the parent of the .app bundle
    on macOS. This keeps GrainPrint portable and avoids OS-specific AppData
    directories.
    """
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            parts = executable.parts
            if ".app" in parts:
                app_index = len(parts) - 1 - parts[::-1].index(".app")
                app_bundle = Path(*parts[: app_index + 1])
                return app_bundle.parent
        return executable.parent
    return Path(__file__).resolve().parents[2]


BASE_DIR = _portable_base()
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "grainprint.duckdb"
DB_URL = f"duckdb:///{DB_PATH}"
SEED_DB_PATH = Path(__file__).with_name("data") / "grainprint.duckdb"


def ensure_database() -> None:
    """Create the local data directory and seed it on first launch."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    latest_backup = DATA_DIR / "backup" / "grainprint_latest.duckdb"
    if not DB_PATH.exists():
        if latest_backup.exists():
            shutil.copy2(latest_backup, DB_PATH)
            return
    if not DB_PATH.exists() and SEED_DB_PATH.exists():
        shutil.copy2(SEED_DB_PATH, DB_PATH)


ensure_database()
