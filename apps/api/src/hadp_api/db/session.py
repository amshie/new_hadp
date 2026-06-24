"""FastAPI request-scoped database session dependency."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from hadp_api.db.engine import get_sessionmaker


def get_db() -> Iterator[Session]:
    """Yield one session/transaction per request; commit on success, roll back on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
