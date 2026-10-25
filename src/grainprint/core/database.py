"""The application's single-writer DuckDB access layer.

DuckDB is an embedded database: a database file may only have one writing
process.  The UI used to open a fresh pooled connection for every button
click, which made an accidental second GrainPrint process fail unpredictably.
This module deliberately uses one in-process connection and serialises every
read/write through a re-entrant lock.  Write commands get one transaction.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from grainprint.config import DB_PATH, ensure_database


class DatabaseInUseError(RuntimeError):
    """Raised when another GrainPrint process owns the DuckDB file."""


_database_lock = threading.RLock()


def _make_engine():
    # StaticPool avoids a collection of independently-opened DuckDB connections
    # within the same Flet process.  The process-level lock below serialises use.
    return create_engine(
        f"duckdb:///{DB_PATH}",
        poolclass=StaticPool,
        connect_args={"config": {"access_mode": "automatic"}},
    )


def _is_lock_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "could not set lock" in text or "conflicting lock" in text or "file is already open" in text


ensure_database()
try:
    engine = _make_engine()
    # Force opening now so a file-lock error is translated before the user edits.
    with engine.connect():
        pass
except Exception as exc:  # pragma: no cover - platform-specific DuckDB wording
    if _is_lock_error(exc):
        raise DatabaseInUseError(
            f"数据库正在被另一份 GrainPrint 使用：{DB_PATH}\n"
            "请关闭另一份 GrainPrint 后再打开本软件。"
        ) from exc
    raise

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _migrate_schema():
    """Apply only additive compatibility changes for existing user databases."""
    if not DB_PATH.exists():
        return
    with _database_lock:
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    "ALTER TABLE marker_associations ADD COLUMN IF NOT EXISTS notes2 TEXT"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE markers ADD COLUMN IF NOT EXISTS notes TEXT"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE markers ADD COLUMN IF NOT EXISTS notes2 TEXT"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE crops ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE subspecies ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0"
                )
                # v0.4.0 stored notes only on individual associations.  New
                # versions make them properties of the material itself; adopt
                # the first existing non-empty values so old projects keep
                # their classification and source after upgrade.
                conn.exec_driver_sql("""
                    UPDATE markers AS m
                    SET notes = (
                        SELECT a.notes FROM marker_associations AS a
                        WHERE a.marker_id = m.id AND a.notes IS NOT NULL AND a.notes <> ''
                        ORDER BY a.id LIMIT 1
                    )
                    WHERE (m.notes IS NULL OR m.notes = '')
                """)
                conn.exec_driver_sql("""
                    UPDATE markers AS m
                    SET notes2 = (
                        SELECT a.notes2 FROM marker_associations AS a
                        WHERE a.marker_id = m.id AND a.notes2 IS NOT NULL AND a.notes2 <> ''
                        ORDER BY a.id LIMIT 1
                    )
                    WHERE (m.notes2 IS NULL OR m.notes2 = '')
                """)
        except Exception:
            # A brand-new DB is initialised below; no destructive fallback here.
            pass


_migrate_schema()


@contextmanager
def get_session():
    """Use one serialised transaction per application service command.

    An exception rolls back the entire command.  It never creates, replaces,
    or resets the database; database loss must remain explicit user action.
    """
    with _database_lock:
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            if _is_lock_error(exc):
                raise DatabaseInUseError(
                    f"数据库正在被另一份 GrainPrint 使用：{DB_PATH}\n"
                    "本次操作没有保存，请关闭另一份软件后重试。"
                ) from exc
            raise
        finally:
            session.close()


def init_db():
    from grainprint.core.models import Base
    with _database_lock:
        Base.metadata.create_all(engine)


def reset_db():
    """Explicit destructive reset, retained only for the visible user command."""
    global engine, SessionLocal
    with _database_lock:
        engine.dispose()
        if DB_PATH.exists():
            DB_PATH.unlink()
        engine = _make_engine()
        SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
        init_db()


if not DB_PATH.exists():
    init_db()
