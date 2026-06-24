"""Authentication provider seam.

`CLAUDE.md`: identity is standards-based OIDC; local development may use a local
provider. The production OIDC provider is a gated vendor decision and is therefore a
clearly-labeled stub that fails visibly rather than impersonating a real integration.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.config import Settings
from hadp_api.modules.identity.models import User


class AuthProvider(Protocol):
    name: str

    def resolve_user(self, db: Session, identifier: str) -> User | None:
        """Resolve an authenticated principal to a local User, or None."""
        ...


class DevAuthProvider:
    """DEV/TEST ONLY. Resolves a seeded user by email with no credential check.

    This is a development shortcut, not an authentication mechanism. It refuses to run
    in production via `get_auth_provider`, and it only ever resolves pre-seeded
    synthetic users.
    """

    name = "dev"

    def resolve_user(self, db: Session, identifier: str) -> User | None:
        return db.execute(
            select(User).where(User.email == identifier.lower(), User.is_active.is_(True))
        ).scalar_one_or_none()


class OidcAuthProvider:
    """Production OIDC provider — intentionally not implemented.

    Selecting and integrating an OIDC provider is a gated vendor decision (EU data
    residency, sub-processor review). This stub fails visibly so the absence of a real
    integration can never be mistaken for a working one.
    """

    name = "oidc"

    def resolve_user(self, db: Session, identifier: str) -> User | None:
        raise NotImplementedError(
            "Production OIDC provider is not configured. Selecting an OIDC vendor is a "
            "gated decision (see CLAUDE.md 'Decisions intentionally left configurable')."
        )


def get_auth_provider(settings: Settings) -> AuthProvider:
    if settings.is_production:
        # Never expose the dev provider in production.
        return OidcAuthProvider()
    return DevAuthProvider()
