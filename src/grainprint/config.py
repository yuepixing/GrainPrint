from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _storage_base() -> Path:
    """Return Flet's writable application-storage directory.

    Flet 0.86+ sets FLET_APP_STORAGE_DATA to a writable, app-private directory
    for built apps. In development, use the project's current working directory.
    """
    configured = os.getenv("FLET_APP_STORAGE_DATA")
    if configured:
        return Path(configured)
    return Path.cwd()


BASE_DIR = _storage_base()
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "grainprint.duckdb"
DB_URL = f"duckdb:///{DB_PATH}"
SEED_DB_PATH = Path(__file__).with_name("data") / "grainprint.duckdb"


def ensure_database() -> None:
    """Create the writable data directory and seed it on first launch."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists() and SEED_DB_PATH.exists():
        shutil.copy2(SEED_DB_PATH, DB_PATH)


ensure_database()
