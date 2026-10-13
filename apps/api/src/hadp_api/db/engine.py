"""Engine, session factory, and tenant row-level-security context.

The application connects as the non-superuser role `hadp_app`, so PostgreSQL RLS
policies are enforced. Each request runs in a single transaction; tenant scope is
applied with `set_config(..., is_local => true)` so it is transaction-scoped and
cannot leak across pooled connections.
"""

from __future__ import annotations

import threading
import uuid

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from hadp_api.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
# Sync handlers run in a thread pool: two first requests must not build two engines.
_init_lock = threading.Lock()


# Tables (and other relations) of the application's schemas whose owner the connecting role
# is, or acts as by membership. The system schemas, and every temporary schema, are not ours.
_OWNED_RELATIONS = text(
    "SELECT count(*) FROM pg_class c "
    "JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE n.nspname <> 'information_schema' AND left(n.nspname, 3) <> 'pg_' "
    "AND pg_has_role(current_user, c.relowner, 'MEMBER')"
)


def _assert_rls_enforceable(engine: Engine) -> None:
    """Refuse to run as a role that bypasses RLS or owns the tables — in every environment.

    A superuser or BYPASSRLS role ignores every tenant policy without an error, so nothing
    else would say that isolation is off (docs/notes/0005). An owner is bound by the
    policies (every tenant table FORCEs them), but not by the REVOKEs that keep the audit
    trail and the consent events append-only, and it can switch row-level security off for
    its tables — so the role that owns them, or is a member of their owner, is refused too.
    Development and tests are held to the same rule: a setup that runs the app as
    `postgres` shows cross-tenant behaviour production will never have.
    """
    with engine.connect() as conn:
        is_superuser = conn.execute(text("SELECT current_setting('is_superuser')")).scalar_one()
        bypass = conn.execute(
            text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).scalar_one()
        owned = conn.execute(_OWNED_RELATIONS).scalar_one()
    if is_superuser == "on" or bool(bypass):
        raise RuntimeError(
            "Refusing to start: the application DB role bypasses row-level security. "
            "Set APP_DATABASE_URL to a non-superuser role (e.g. hadp_app)."
        )
    if owned:
        raise RuntimeError(
            "Refusing to start: the application DB role owns tables, or is a member of their "
            "owner — an owner can switch row-level security off and is not bound by the "
            "grants that keep the audit trail append-only. Set APP_DATABASE_URL to the "
            "application role (e.g. hadp_app), which owns nothing."
        )


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        with _init_lock:
            if _engine is None:
                engine = create_engine(
                    get_settings().effective_app_database_url,
                    pool_pre_ping=True,
                    future=True,
                    # A database host that does not answer fails the start, not hangs it.
                    connect_args={"connect_timeout": 10},
                )
                # Checked BEFORE the engine is kept: a refused engine must not be handed out
                # by the next call. (It was kept once — the first request failed and every
                # later one ran with RLS bypassed.)
                try:
                    _assert_rls_enforceable(engine)
                except BaseException:
                    engine.dispose()
                    raise
                # The session factory first: nobody may see an engine without one.
                _SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
                _engine = engine
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
