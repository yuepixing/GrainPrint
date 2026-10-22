from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from grainprint.config import DB_PATH, ensure_database


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
        DB_PATH.unlink()

    engine = create_engine(f"duckdb:///{DB_PATH}")
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    init_db()


if not DB_PATH.exists():
    init_db()
