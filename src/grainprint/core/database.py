from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from datetime import datetime
import shutil

from grainprint.config import DATA_DIR, DB_PATH, ensure_database


ensure_database()

engine = create_engine(f"duckdb:///{DB_PATH}")
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _migrate_schema():
    """轻量迁移：为旧库补充 notes2 列。"""
    if not DB_PATH.exists():
        return
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE marker_associations ADD COLUMN IF NOT EXISTS notes2 TEXT"
            )
            conn.exec_driver_sql(
                "ALTER TABLE crops ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0"
            )
            conn.exec_driver_sql(
                "ALTER TABLE subspecies ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0"
            )
    except Exception:
        # 新建库初始化时由 SQLAlchemy 建表，不需要 ALTER。
        pass


_migrate_schema()


def _backup_on_startup():
    """每次启动保留 latest，并在每天首次启动时保留日期版备份。"""
    if not DB_PATH.exists():
        return None

    # 先关闭连接池，确保复制的 DuckDB 文件不依赖未 checkpoint 的 WAL。
    if "engine" in globals():
        engine.dispose()

    backup_dir = DATA_DIR / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    date_name = datetime.now().strftime("%Y%m%d")
    backup_path = backup_dir / f"grainprint_{date_name}.duckdb"
    latest_path = backup_dir / "grainprint_latest.duckdb"

    if backup_path.exists():
        pass
    else:
        import shutil
        shutil.copy2(DB_PATH, backup_path)

    import shutil
    shutil.copy2(DB_PATH, latest_path)
    return latest_path


_backup_on_startup()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    from grainprint.core.models import Base
    Base.metadata.create_all(engine)


def reset_db():
    global engine, SessionLocal

    engine.dispose()

    if DB_PATH.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = DB_PATH.with_name(f"{DB_PATH.name}.bak_{stamp}")
        shutil.copy2(DB_PATH, backup)

        # 删除时仍避免直接 unlink 数据文件；rename 为 damaged 保留现场。
        damaged = DB_PATH.with_name(f"{DB_PATH.name}.damaged_{stamp}")
        DB_PATH.rename(damaged)

    engine = create_engine(f"duckdb:///{DB_PATH}")
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    init_db()

    # 返回备份路径，方便 UI 提示。
    return {"backup": backup if 'backup' in locals() else None}


if not DB_PATH.exists():
    init_db()
