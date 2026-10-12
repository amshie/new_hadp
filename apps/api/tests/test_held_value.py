"""A value the platform could not normalize keeps its number.

Until normalization version norm-2 a value the terminology did not know — or in a unit
without an approved conversion — had no number at all on the read side: the timeline, the
tables and the interpretation evidence showed "—" under a name, although the source had
written a number, a unit and a reference interval. Such a value is still not normalized and
still waits for a human; once published it is shown as the source wrote it, in the source's
unit, with the source's bounds — and it takes no part in a change calculation.
"""

from __future__ import annotations

import importlib.util
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from hadp_api.modules.enums import ReviewStatus, Role, ValueType
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.observations.service import held_value
from tests.helpers import login_as
from tests.test_interpretation_author_api import _payload

DAY = {"observed_at": "2025-06-10T00:00:00Z", "observed_at_is_date_only": True}


def _clinician(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"{slug}@synthetic.example",
        tenant_name=f"Held {slug}",
        tenant_slug=f"held-{slug}",
        role=Role.CLINICIAN,
    )


def _import(client, values: list[dict]) -> str:  # type: ignore[no-untyped-def, type-arg]
    """Create a patient, import the values and publish whatever went to review."""
    pid = client.post("/api/v1/patients", json={"display_name": "Synthetic Held"}).json()["id"]
    result = client.post(f"/api/v1/patients/{pid}/imports", json={"values": values})
    assert result.status_code == 201, result.text
    for item_id in result.json()["review_item_ids"]:
        resolved = client.post(
            f"/api/v1/review-items/{item_id}/resolve", json={"decision": "publish"}
        )
        assert resolved.status_code == 200, resolved.text
    return pid


def _timeline(client, pid: str) -> dict[str, dict]:  # type: ignore[no-untyped-def, type-arg]
    points = client.get(f"/api/v1/patients/{pid}/observations").json()
    return {p["original_name"]: p for p in points}


def test_the_timeline_shows_each_value_in_the_form_the_platform_holds(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "forms")
    pid = _import(
        client,
        [
            # Unknown to the catalog: the source's number, unit and bounds.
            {
                "original_name": "Zink",
                "original_value": "65",
                "original_unit": "µg/dL",
                "reference_low": "70",
                "reference_high": "120",
                **DAY,
            },
            # Known, in a unit with no approved conversion: the same.
            {
                "original_name": "Ferritin",
                "original_value": "85",
                "original_unit": "ng/mL",
                "reference_low": "30",
                "reference_high": "400",
                **DAY,
            },
            # Known, converted by an approved factor.
            {
                "original_name": "LDL Cholesterol",
                "original_value": "130",
                "original_unit": "mg/dL",
                "reference_low": "0",
                "reference_high": "116",
                **DAY,
            },
            # Known, in its canonical unit written the usual way.
            {
                "original_name": "Creatinine",
                "original_value": "80",
                "original_unit": "µmol/l",
                **DAY,
            },
            # Not a number at all.
            {"original_name": "HIV-1/2 Screening", "original_value": "reaktiv", **DAY},
        ],
    )

    by_name = _timeline(client, pid)

    zinc = by_name["Zink"]
    assert (zinc["value"], zinc["unit"]) == ("65", "µg/dL")
    assert (zinc["normalized"], zinc["converted"]) == (False, False)
    assert (zinc["reference_low"], zinc["reference_high"]) == ("70", "120")
    assert (zinc["kpi_code"], zinc["metric_code"]) == (None, None)

    ferritin = by_name["Ferritin"]
    assert (ferritin["value"], ferritin["unit"]) == ("85", "ng/mL")
    assert (ferritin["normalized"], ferritin["converted"]) == (False, False)
    assert (ferritin["reference_low"], ferritin["reference_high"]) == ("30", "400")
    assert ferritin["kpi_code"] == "immune.ferritin"

    ldl = by_name["LDL Cholesterol"]
    assert (ldl["value"], ldl["unit"]) == ("3.3617740", "mmol/L")
    assert (ldl["normalized"], ldl["converted"]) == (True, True)
    # The source's own writing travels with the converted number.
    assert (ldl["original_value"], ldl["original_unit"]) == ("130", "mg/dL")
    assert (ldl["reference_low"], ldl["reference_high"]) == ("0.0000000", "2.9997368")

    creatinine = by_name["Creatinine"]
    assert (creatinine["value"], creatinine["unit"]) == ("80", "umol/L")
    assert (creatinine["normalized"], creatinine["converted"]) == (True, False)
    assert (creatinine["original_value"], creatinine["original_unit"]) == ("80", "µmol/l")
    assert (creatinine["kpi_code"], creatinine["metric_code"]) == ("regen.creatinine", None)

    text_result = by_name["HIV-1/2 Screening"]
    assert (text_result["value"], text_result["unit"]) == (None, None)
    assert text_result["original_value"] == "reaktiv"
    assert (text_result["normalized"], text_result["converted"]) == (False, False)


def test_a_value_that_is_not_normalized_takes_no_part_in_a_change(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """No change is computed for a value held in the source's unit: neither between two such
    values, nor between one and a normalized value of the same KPI. And it never becomes the
    "previous" value of a later normalized one."""
    _clinician(client, admin_session, "delta")

    def on(day: str) -> dict[str, object]:
        return {"observed_at": f"2025-06-{day}T00:00:00Z", "observed_at_is_date_only": True}

    pid = _import(
        client,
        [
            {"original_name": "Zink", "original_value": "65", "original_unit": "µg/dL", **on("01")},
            {"original_name": "Zink", "original_value": "80", "original_unit": "µg/dL", **on("20")},
            {
                "original_name": "LDL Cholesterol",
                "original_value": "3.0",
                "original_unit": "mmol/L",
                **on("02"),
            },
            # The same KPI in a unit the registry has no factor for (catalytic concentration).
            {
                "original_name": "LDL Cholesterol",
                "original_value": "9.9",
                "original_unit": "µkat/L",
                **on("10"),
            },
            {
                "original_name": "LDL Cholesterol",
                "original_value": "2.5",
                "original_unit": "mmol/L",
                **on("21"),
            },
        ],
    )

    points = client.get(f"/api/v1/patients/{pid}/observations").json()
    changes = {
        (p["original_name"], p["original_value"]): (p["delta_vs_previous"], p["comparability"])
        for p in points
    }

    assert changes[("Zink", "65")] == (None, None)
    assert changes[("Zink", "80")] == (None, None)
    assert changes[("LDL Cholesterol", "9.9")] == (None, None)
    # 2.5 compares against 3.0 — the value in between, held in another unit, is skipped.
    assert changes[("LDL Cholesterol", "2.5")] == ("-0.5", "comparable")
    first = next(p for p in points if p["original_value"] == "3.0")
    last = next(p for p in points if p["original_value"] == "2.5")
    assert last["previous_observation_id"] == first["observation_id"]


def test_interpretation_evidence_shows_the_held_value_and_the_catalog_identity(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """A clinician may cite a published value the catalog does not know. The evidence then
    shows the source's number, unit and bounds — not "—" — and, for a catalog KPI, its code."""
    _clinician(client, admin_session, "evidence")
    pid = _import(
        client,
        [
            {
                "original_name": "Ferritin",
                "original_value": "85",
                "original_unit": "ng/mL",
                "reference_low": "30",
                "reference_high": "400",
                **DAY,
            }
        ],
    )
    obs_id = _timeline(client, pid)["Ferritin"]["observation_id"]
    authored = client.post(f"/api/v1/patients/{pid}/interpretation-runs", json=_payload(obs_id))
    assert authored.status_code == 201, authored.text

    matrix = client.get(f"/api/v1/patients/{pid}/interpretation").json()
    cited = matrix["domains"][0]["cells"][0]["evidence"][0]

    assert (cited["value"], cited["unit"]) == ("85", "ng/mL")
    assert cited["reference"] == "30–400 ng/mL"
    assert (cited["kpi_code"], cited["metric_code"]) == ("immune.ferritin", None)


def _legacy_row(tenant_id: uuid.UUID, patient_id: uuid.UUID, **fields: object) -> Observation:
    values: dict[str, object] = {
        "tenant_id": tenant_id,
        "patient_id": patient_id,
        "original_name": "Legacy",
        "original_value": "1",
        "value_type": ValueType.NUMERIC,
        "normalization_version": "norm-1",
        "observed_at": datetime(2025, 6, 10, tzinfo=UTC),
        "observed_at_is_date_only": True,
        "received_at": datetime(2025, 6, 11, tzinfo=UTC),
        "review_status": ReviewStatus.PUBLISHED,
    }
    values.update(fields)
    return Observation(**values)


def test_the_migration_gives_stored_rows_the_number_their_source_wrote(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """norm-1 wrote the NORMALIZED value into numeric_value: nothing for an unknown analyte,
    the converted number for a converted one. Migration 0018 reads the number from the
    immutable source string, with the import's own grammar."""
    path = Path(__file__).parents[1] / "alembic/versions/0018_observation_source_number.py"
    spec = importlib.util.spec_from_file_location("migration_0018", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    _user, tenant = _clinician(client, admin_session, "migration")
    pid = uuid.UUID(
        client.post("/api/v1/patients", json={"display_name": "Synthetic Legacy"}).json()["id"]
    )
    legacy = {
        # name: (original_value, numeric_value as norm-1 stored it, normalized_value)
        "unknown analyte": ("85", None, None),
        "decimal comma": (" 2,80 ", None, None),
        "converted": ("130", Decimal("3.361774"), Decimal("3.361774")),
        "same unit": ("2.8", Decimal("2.8"), Decimal("2.8")),
        "text result": ("reaktiv", None, None),
        "flagged": ("12,4 H", None, None),
        "comparator": ("<0.5", None, None),
        "thousands separator": ("1.234,5", None, None),
    }
    for name, (original, numeric, normalized) in legacy.items():
        admin_session.add(
            _legacy_row(
                tenant.id,
                pid,
                original_name=name,
                original_value=original,
                numeric_value=numeric,
                normalized_value=normalized,
                normalized_unit="mmol/L" if normalized is not None else None,
            )
        )
    admin_session.flush()

    admin_session.execute(migration.BACKFILL)
    admin_session.expire_all()

    rows = {
        o.original_name: o
        for o in admin_session.execute(
            select(Observation).where(Observation.patient_id == pid)
        ).scalars()
    }
    assert {name: row.numeric_value for name, row in rows.items()} == {
        "unknown analyte": Decimal("85"),
        "decimal comma": Decimal("2.80"),
        "converted": Decimal("130"),  # the source's number, no longer the converted one
        "same unit": Decimal("2.8"),
        "text result": None,
        "flagged": None,
        "comparator": None,
        "thousands separator": None,
    }
    # The read side: a normalized row is unchanged, an un-normalized one now has its number.
    assert held_value(rows["converted"]) == (Decimal("3.361774"), "mmol/L")
    assert held_value(rows["unknown analyte"]) == (Decimal("85"), None)
    assert held_value(rows["text result"]) == (None, None)
    admin_session.rollback()
