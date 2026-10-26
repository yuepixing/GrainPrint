"""Cross-platform process lock for the desktop application."""
from __future__ import annotations

import atexit
import os
import sys
from pathlib import Path

from grainprint.config import DATA_DIR

_lock_file = None


def acquire_or_exit() -> None:
    """Refuse a second GrainPrint process before it can touch DuckDB."""
    global _lock_file
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "grainprint.instance.lock"
    handle = open(path, "a+b")
    handle.seek(0)
    if not handle.read(1):
        handle.seek(0)
        handle.write(b"1")
        handle.flush()
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        _show_already_running_message()
        raise SystemExit(1)
    _lock_file = handle
    atexit.register(_release)


def _release() -> None:
    global _lock_file
    if _lock_file is None:
        return
    try:
        if os.name == "nt":
            import msvcrt
            _lock_file.seek(0)
            msvcrt.locking(_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        _lock_file.close()
        _lock_file = None


def _show_already_running_message() -> None:
    message = "GrainPrint 已在运行。请在已打开的软件窗口中继续操作，不要重复启动。"
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "GrainPrint", 0x10)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)
