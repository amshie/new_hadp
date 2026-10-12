"""FastAPI request-scoped database session dependency."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
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


# The ONE way a route obtains its session: `db: Session = RequestSession`.
#
# `scope="function"` ends the dependency — the commit above — when the path operation
# returns, BEFORE the response is sent. FastAPI's default ("request") commits AFTER the
# response: the client would hear "saved" for a write that a failing commit then drops, and
# a request sent right after (select the clinic straight after logging in) could miss it.
# Declared once because two declarations with different scopes would be two sessions in one
# request (tests/test_commit_before_response.py guards both properties).
RequestSession = Depends(get_db, scope="function")
