from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from grainprint.config import DB_PATH, ensure_database


ensure_database()

engine = create_engine(f"duckdb:///{DB_PATH}")
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


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
