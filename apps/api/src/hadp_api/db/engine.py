"""Engine, session factory, and tenant row-level-security context.

The application connects as the non-superuser role `hadp_app`, so PostgreSQL RLS
policies are enforced. Each request runs in a single transaction; tenant scope is
applied with `set_config(..., is_local => true)` so it is transaction-scoped and
cannot leak across pooled connections.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from hadp_api.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _assert_rls_enforceable(engine: Engine) -> None:
    """Refuse to run as a role that bypasses RLS (defense-in-depth for production)."""
    with engine.connect() as conn:
        is_superuser = conn.execute(text("SELECT current_setting('is_superuser')")).scalar_one()
        bypass = conn.execute(
            text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).scalar_one()
    if is_superuser == "on" or bool(bypass):
        raise RuntimeError(
            "Refusing to start: the application DB role bypasses row-level security. "
            "Set APP_DATABASE_URL to a non-superuser role (e.g. hadp_app)."
        )


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.effective_app_database_url,
            pool_pre_ping=True,
            future=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
        if settings.is_production:
            _assert_rls_enforceable(_engine)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def reset_engine() -> None:
    """Drop cached engine/sessionmaker (used by tests that switch DSNs)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def set_tenant_context(
    session: Session, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """Bind the current tenant (and optionally user) to the active transaction for RLS.

    Uses set_config with is_local => true so the setting is reset at commit/rollback.
    The first statement also starts the transaction the request will run in. `user_id`
    may be None for patient-facing access (via a scoped link) where no staff user acts;
    RLS policies key only on `app.current_tenant`.
    """
    session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    session.execute(
        text("SELECT set_config('app.current_user', :uid, true)"),
        {"uid": str(user_id) if user_id is not None else ""},
    )
