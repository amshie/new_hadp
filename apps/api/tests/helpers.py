"""Shared test helpers: synthetic factories and the auth flow.

Factories use the admin (superuser) session so RLS does not block test setup, and they
COMMIT so the application connection (the `hadp_app` role) can see the rows.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from hadp_api.modules.enums import Role
from hadp_api.modules.identity.models import User
from hadp_api.modules.tenancy.models import Membership, Tenant


def make_user(admin_session: Session, *, email: str, name: str = "Synthetic Staff") -> User:
    user = User(email=email.lower(), display_name=name, is_synthetic=True)
    admin_session.add(user)
    admin_session.flush()
    return user


def make_tenant(admin_session: Session, *, name: str, slug: str) -> Tenant:
    tenant = Tenant(name=name, slug=slug, is_synthetic=True)
    admin_session.add(tenant)
    admin_session.flush()
    return tenant


def make_membership(
    admin_session: Session, *, user_id: uuid.UUID, tenant_id: uuid.UUID, role: Role
) -> Membership:
    membership = Membership(user_id=user_id, tenant_id=tenant_id, role=role)
    admin_session.add(membership)
    admin_session.flush()
    return membership


def provision_staff(
    admin_session: Session,
    *,
    email: str,
    tenant_name: str,
    tenant_slug: str,
    role: Role,
) -> tuple[User, Tenant]:
    """Create a user + tenant + membership and COMMIT so the app connection sees them."""
    user = make_user(admin_session, email=email)
    tenant = make_tenant(admin_session, name=tenant_name, slug=tenant_slug)
    make_membership(admin_session, user_id=user.id, tenant_id=tenant.id, role=role)
    admin_session.commit()
    return user, tenant


def login(client, email: str):  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/auth/dev-login", json={"email": email})
    assert resp.status_code == 200, resp.text
    return resp


def select_tenant(client, tenant_id) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/tenancy/select-tenant", json={"tenant_id": str(tenant_id)})
    assert resp.status_code == 200, resp.text


def login_as(
    client, admin_session, *, email, tenant_name, tenant_slug, role
) -> tuple[User, Tenant]:  # type: ignore[no-untyped-def]
    user, tenant = provision_staff(
        admin_session, email=email, tenant_name=tenant_name, tenant_slug=tenant_slug, role=role
    )
    login(client, email)
    select_tenant(client, tenant.id)
    return user, tenant
