"""
Postgres engine/session factory. Kept separate from offline_queue.py
(which handles the local SQLite buffer) so the two datastores never get
confused with each other.
"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import config

engine = create_engine(config.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session():
    """
    Usage:
        with get_session() as session:
            session.add(obj)
    Raises whatever the underlying DB error is (e.g. OperationalError when
    Postgres is unreachable) so callers can decide to fall back to the
    offline queue.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_postgres_reachable() -> bool:
    """Cheap connectivity check used before deciding to write directly vs. queue."""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except Exception:
        return False
