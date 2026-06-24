"""Server-side session tokens.

A random token is returned to the client in an httpOnly cookie; only its SHA-256 hash
is stored. Sessions are short-lived and revocable.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.modules.identity.models import AuthSession


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_session(db: Session, *, user_id: uuid.UUID, ttl_seconds: int) -> tuple[AuthSession, str]:
    raw_token = secrets.token_urlsafe(32)
    session = AuthSession(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
    )
    db.add(session)
    db.flush()
    return session, raw_token


def get_active_session(db: Session, raw_token: str) -> AuthSession | None:
    session = db.execute(
        select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token))
    ).scalar_one_or_none()
    if session is None or session.revoked_at is not None:
        return None
    if session.expires_at <= datetime.now(UTC):
        return None
    return session


def revoke_session(db: Session, session: AuthSession) -> None:
    session.revoked_at = datetime.now(UTC)
    db.flush()
