"""A value the platform could not normalize keeps its number.

Until normalization version norm-2 a value the import did not normalize — a name it does not
act on by itself, or a unit without an approved conversion — had no number at all on the read
side: the timeline, the tables and the interpretation evidence showed "—" under a name,
although the source had written a number, a unit and a reference interval. Such a value is
still not normalized and still waits for a human; once published it is shown as the source
wrote it, in the source's unit, with the source's bounds — and it takes no part in a change
calculation.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import ProgrammingError

from hadp_api.config import get_settings
from hadp_api.modules.enums import ReviewStatus, Role, ValueType
from hadp_api.modules.imports.normalize import is_one_number
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
            # A catalog KPI the import does not act on by itself: the same, with its KPI.
            {
                "original_name": "Ferritin",
                "original_value": "85",
                "original_unit": "ng/mL",
                "reference_low": "30",
                "reference_high": "400",
                **DAY,
            },
            # One of the six names, converted by an approved factor.
            {
                "original_name": "LDL Cholesterol",
                "original_value": "130",
                "original_unit": "mg/dL",
                "reference_low": "0",
                "reference_high": "116",
                **DAY,
            },
            # A catalog KPI in the catalog's own unit — still the source's writing.
            {
                "original_name": "Creatinine",
                "original_value": "80",
                "original_unit": "µmol/l",
                **DAY,
            },
            # Not a number at all.
            {"original_name": "HIV-1/2 Screening", "original_value": "reaktiv", **DAY},
            # A number that reads two ways: the source's wording, and no number.
            {
                "original_name": "Thrombozyten",
                "original_value": "98.000",
                "original_unit": "/µl",
                "reference_low": "150.000",
                "reference_high": "400.000",
                **DAY,
            },
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
    assert (creatinine["value"], creatinine["unit"]) == ("80", "µmol/l")
    assert (creatinine["normalized"], creatinine["converted"]) == (False, False)
    assert (creatinine["kpi_code"], creatinine["metric_code"]) == ("regen.creatinine", None)

    text_result = by_name["HIV-1/2 Screening"]
    assert (text_result["value"], text_result["unit"]) == (None, None)
    assert text_result["original_value"] == "reaktiv"
    assert (text_result["normalized"], text_result["converted"]) == (False, False)

    platelets = by_name["Thrombozyten"]
    assert (platelets["value"], platelets["original_value"]) == (None, "98.000")
    assert (platelets["reference_low"], platelets["reference_high"]) == (None, None)


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
    """A clinician may cite a published value the import did not normalize. The evidence then
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


def test_the_held_unit_of_a_value_that_is_not_normalized_is_the_sources_unit_trimmed() -> None:
    tenant, patient = uuid.uuid4(), uuid.uuid4()
    for written, held in (("  ng/mL ", "ng/mL"), ("µg/dL", "µg/dL"), ("   ", None), (None, None)):
        row = _legacy_row(tenant, patient, original_unit=written, numeric_value=Decimal("85"))
        assert held_value(row) == (Decimal("85"), held)
    normalized = _legacy_row(
        tenant,
        patient,
        original_unit=" mg/dL ",
        numeric_value=Decimal("130"),
        normalized_value=Decimal("3.361774"),
        normalized_unit="mmol/L",
    )
    assert held_value(normalized) == (Decimal("3.361774"), "mmol/L")


def _migration_0018():  # type: ignore[no-untyped-def]
    path = Path(__file__).parents[1] / "alembic/versions/0018_observation_source_number.py"
    spec = importlib.util.spec_from_file_location("migration_0018", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


# What norm-1 stored, and what the source's number is.
# name: (original_value, numeric_value as norm-1 stored it, normalized_value, expected)
LEGACY: dict[str, tuple[str, Decimal | None, Decimal | None, Decimal | None]] = {
    "unknown analyte": ("85", None, None, Decimal("85")),
    "decimal comma": (" 2,80 ", None, None, Decimal("2.80")),
    # The source's number, no longer the converted one.
    "converted": ("130", Decimal("3.361774"), Decimal("3.361774"), Decimal("130")),
    "same unit": ("2.8", Decimal("2.8"), Decimal("2.8"), Decimal("2.8")),
    "same number, another scale": ("2.80", Decimal("2.8"), Decimal("2.8"), Decimal("2.80")),
    "text result": ("reaktiv", None, None, None),
    "flagged": ("12,4 H", None, None, None),
    "comparator": ("<0.5", None, None, None),
    "two marks": ("1.234,5", None, None, None),
    # A number that reads two ways is not read — also where norm-1 had read it.
    "grouped": ("4.000", Decimal("4.000"), Decimal("4.000"), None),
    "grouped comma": ("1,250", None, None, None),
    "grouped, padded": ("04.000", None, None, None),
    "grouped, signed": ("-1.250", None, None, None),
    "grouped, two lead digits": ("12.345", None, None, None),
    "grouped, three lead digits": ("150.000", None, None, None),
    "zeros lead": ("00.500", None, None, Decimal("0.500")),
    "four lead digits": ("1000.000", None, None, Decimal("1000.000")),
    "signed": ("+2.5", None, None, Decimal("2.5")),
    "negative": ("-0.5", None, None, Decimal("-0.5")),
    "bare fraction": (".5", None, None, Decimal("0.5")),
    "trailing mark": ("5.", None, None, Decimal("5")),
    "exponent": ("5.00E+01", None, None, Decimal("50.0")),
    "negative exponent": ("25e-1", None, None, Decimal("2.5")),
    "grouped shape with exponent": ("1.234e2", None, None, Decimal("123.4")),
    "three-digit exponent": ("1e100", None, None, None),
    "tab and line feed": ("\t3,4\r\n", None, None, Decimal("3.4")),
    # The letter v is not white space (PostgreSQL has no escape for the vertical tab).
    "trailing v": ("12,4 v", None, None, None),
    "leading v": ("v5", None, None, None),
    "vertical tab": ("\x0b 7,5 \x0b", None, None, Decimal("7.5")),
    "ascii separators": ("\x1c6\x1f", None, None, Decimal("6")),
    # Fails closed: the import would read 5, the migration leaves the source's wording.
    "no-break space": ("5\u00a0", None, None, None),
}


def _store_legacy(admin_session, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> None:  # type: ignore[no-untyped-def]
    for name, (original, numeric, normalized, _expected) in LEGACY.items():
        admin_session.add(
            _legacy_row(
                tenant_id,
                patient_id,
                original_name=name,
                original_value=original,
                numeric_value=numeric,
                normalized_value=normalized,
                normalized_unit="mmol/L" if normalized is not None else None,
            )
        )
    admin_session.flush()


def _numbers(admin_session, patient_id: uuid.UUID) -> dict[str, Observation]:  # type: ignore[no-untyped-def]
    admin_session.expire_all()
    rows = admin_session.execute(select(Observation).where(Observation.patient_id == patient_id))
    return {o.original_name: o for o in rows.scalars()}


def test_the_migration_gives_stored_rows_the_number_their_source_wrote(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """norm-1 wrote the NORMALIZED value into numeric_value: nothing for an unknown analyte,
    the converted number for a converted one. Migration 0018 reads the number from the
    immutable source string, with the import's own grammar."""
    migration = _migration_0018()
    _user, tenant = _clinician(client, admin_session, "migration")
    pid = uuid.UUID(
        client.post("/api/v1/patients", json={"display_name": "Synthetic Legacy"}).json()["id"]
    )
    _store_legacy(admin_session, tenant.id, pid)

    changed = admin_session.execute(migration.BACKFILL).rowcount

    rows = _numbers(admin_session, pid)
    assert {name: row.numeric_value for name, row in rows.items()} == {
        name: expected for name, (_o, _n, _norm, expected) in LEGACY.items()
    }
    # Exactly as written: "2.80" keeps its scale although 2.8 was stored for it.
    assert str(rows["same number, another scale"].numeric_value) == "2.80"
    # The statement agrees with the import's own reading of every ASCII case — the one
    # difference is the no-break space, which the import strips and the migration does not.
    for name, (original, _n, _norm, expected) in LEGACY.items():
        if name != "no-break space":
            assert is_one_number(original) == (expected is not None), name
    # Only rows whose number changes are written: a second run touches nothing.
    assert changed == sum(
        1 for _o, numeric, _norm, expected in LEGACY.values() if str(numeric) != str(expected)
    )
    assert admin_session.execute(migration.BACKFILL).rowcount == 0
    # The read side: a normalized row is unchanged, an un-normalized one now has its number.
    assert held_value(rows["converted"]) == (Decimal("3.361774"), "mmol/L")
    assert held_value(rows["grouped"]) == (Decimal("4.000"), "mmol/L")  # as norm-1 published it
    assert held_value(rows["unknown analyte"]) == (Decimal("85"), None)
    assert held_value(rows["text result"]) == (None, None)

    # And back: the former meaning.
    admin_session.execute(migration.RESTORE)
    rows = _numbers(admin_session, pid)
    assert {name: row.numeric_value for name, row in rows.items()} == {
        name: normalized for name, (_o, _n, normalized, _e) in LEGACY.items()
    }
    admin_session.rollback()


def test_the_migration_runs_through_alembic_in_both_directions(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    """The statements above, as the migration itself runs them — down to the revision before,
    and up again over rows stored in between."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(os.path.join(Path(__file__).parents[1], "alembic.ini"))
    _user, tenant = _clinician(client, admin_session, "alembic")
    pid = uuid.UUID(
        client.post("/api/v1/patients", json={"display_name": "Synthetic Legacy"}).json()["id"]
    )
    try:
        command.downgrade(cfg, "0017_report_rejection_reason")
        _store_legacy(admin_session, tenant.id, pid)
        admin_session.commit()

        command.upgrade(cfg, "head")

        rows = _numbers(admin_session, pid)
        assert {name: row.numeric_value for name, row in rows.items()} == {
            name: expected for name, (_o, _n, _norm, expected) in LEGACY.items()
        }

        command.downgrade(cfg, "0017_report_rejection_reason")
        rows = _numbers(admin_session, pid)
        assert {name: row.numeric_value for name, row in rows.items()} == {
            name: normalized for name, (_o, _n, normalized, _e) in LEGACY.items()
        }
    finally:
        admin_session.rollback()
        command.upgrade(cfg, "head")
        # Alembic configures logging from alembic.ini and switches existing loggers off.
        for existing in logging.Logger.manager.loggerDict.values():
            if isinstance(existing, logging.Logger):
                existing.disabled = False


def test_the_migration_switches_row_security_off_before_it_writes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Both directions: the switch comes first, in the same transaction as the statement."""
    migration = _migration_0018()
    executed: list[object] = []
    monkeypatch.setattr(migration.op, "execute", executed.append)

    migration.upgrade()
    migration.downgrade()

    assert executed == [
        migration.ROW_SECURITY_OFF,
        migration.BACKFILL,
        migration.ROW_SECURITY_OFF,
        migration.RESTORE,
    ]


def test_the_migration_fails_loudly_for_a_role_under_row_level_security(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    """`observations` is under row-level security. Without a tenant bound, the application
    role's UPDATE matches no row and reports success — a migration run by such a role would
    change nothing and say nothing. With row security switched off for the statement, as the
    migration does, the same role is refused."""
    migration = _migration_0018()
    _user, tenant = _clinician(client, admin_session, "rls")
    pid = uuid.UUID(
        client.post("/api/v1/patients", json={"display_name": "Synthetic Legacy"}).json()["id"]
    )
    _store_legacy(admin_session, tenant.id, pid)
    admin_session.commit()

    engine = create_engine(get_settings().effective_app_database_url)
    try:
        with engine.begin() as conn:
            # What would happen without the switch: nothing, silently.
            assert conn.execute(migration.BACKFILL).rowcount == 0
        with pytest.raises(ProgrammingError, match="row-level security"), engine.begin() as conn:
            conn.execute(text(migration.ROW_SECURITY_OFF))
            conn.execute(migration.BACKFILL)
    finally:
        engine.dispose()
    assert _numbers(admin_session, pid)["unknown analyte"].numeric_value is None
