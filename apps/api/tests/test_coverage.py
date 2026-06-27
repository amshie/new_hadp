"""Worklist coverage endpoint: tenant-scoped observation coverage counts, isolation, auth.

Coverage is plain counts/freshness over real observations — NOT a quality score (Gate G1). The
tests pin the counts and prove one tenant's observations never bleed into another's coverage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hadp_api.main import app
from hadp_api.modules.enums import ReviewStatus, Role, ValueType
from hadp_api.modules.observations.models import Observation
from tests.helpers import login, login_as, provision_staff, select_tenant


def _obs(
    admin_session: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: str,
    review_status: ReviewStatus,
    observed_at: datetime,
    reference_low: Decimal | None = None,
) -> None:
    admin_session.add(
        Observation(
            tenant_id=tenant_id,
            patient_id=uuid.UUID(str(patient_id)),
            original_name="Synthetic Marker",
            original_value="1",
            value_type=ValueType.NUMERIC,
            numeric_value=Decimal("1"),
            normalized_value=Decimal("1"),
            normalized_unit="mmol/L",
            reference_low=reference_low,
            normalization_version="test",
            observed_at=observed_at,
            received_at=datetime.now(UTC),
            review_status=review_status,
        )
    )


def test_coverage_requires_authentication(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/worklist/coverage").status_code == 401


def test_coverage_counts_published_and_reference(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, tenant = login_as(
        client,
        admin_session,
        email="cov-a@synthetic.example",
        tenant_name="COV A",
        tenant_slug="cov-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "Coverage Patient"}).json()["id"]
    # 3 observations: 2 published (one carries a reference interval), 1 still pending review.
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        review_status=ReviewStatus.PUBLISHED,
        reference_low=Decimal("0.5"),
        observed_at=datetime(2025, 6, 1, tzinfo=UTC),
    )
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        review_status=ReviewStatus.PUBLISHED,
        observed_at=datetime(2025, 7, 1, tzinfo=UTC),
    )
    _obs(
        admin_session,
        tenant_id=tenant.id,
        patient_id=pid,
        review_status=ReviewStatus.PENDING,
        observed_at=datetime(2025, 5, 1, tzinfo=UTC),
    )
    admin_session.commit()

    body = client.get("/api/v1/worklist/coverage").json()
    assert body["total"] == 3
    assert body["published"] == 2
    assert body["with_reference"] == 1
    assert body["latest_observed_at"].startswith("2025-07-01")


def test_coverage_excludes_other_tenants(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _, ta = login_as(
        client,
        admin_session,
        email="cov-iso-a@synthetic.example",
        tenant_name="COV ISO A",
        tenant_slug="cov-iso-a",
        role=Role.CLINICIAN,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "Iso A"}).json()["id"]
    _obs(
        admin_session,
        tenant_id=ta.id,
        patient_id=pid,
        review_status=ReviewStatus.PUBLISHED,
        observed_at=datetime(2025, 6, 1, tzinfo=UTC),
    )
    admin_session.commit()

    # A fresh tenant B sees an all-zero coverage — A's observations never leak across the boundary.
    provision_staff(
        admin_session,
        email="cov-iso-b@synthetic.example",
        tenant_name="COV ISO B",
        tenant_slug="cov-iso-b",
        role=Role.CLINICIAN,
    )
    with TestClient(app) as cb:
        login(cb, "cov-iso-b@synthetic.example")
        tb = cb.get("/api/v1/tenancy/my-tenants").json()[0]["tenant_id"]
        select_tenant(cb, tb)
        body = cb.get("/api/v1/worklist/coverage").json()
        assert body == {
            "total": 0,
            "published": 0,
            "with_reference": 0,
            "latest_observed_at": None,
        }
