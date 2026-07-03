"""KPI catalog service: seed the catalog (idempotent) and resolve a source term to a KPI code."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.modules.enums import (
    DomainAxis,
    KpiCatalogTier,
    KpiComparisonPolicy,
    KpiExternalCodeStatus,
    KpiMeasurementClass,
    KpiReleaseStatus,
    KpiStatus,
    KpiValueKind,
)
from hadp_api.modules.kpi.catalog_data import (
    CATALOG_VERSION,
    EXTRA_ALIASES,
    VERIFIED_EXTERNAL_CODES,
    kpi_rows,
    kpi_secondary_domain_rows,
)
from hadp_api.modules.kpi.models import (
    KpiAlias,
    KpiCatalog,
    KpiCatalogRelease,
    KpiExternalCode,
    KpiSecondaryDomain,
)


def _aliases_for(rows: list[dict[str, object]]) -> dict[str, str]:
    """Global alias_normalized -> kpi_code. Auto display-name alias + explicit extras.

    A collision (one alias mapping to two different KPIs) is a seed failure, never a runtime guess.
    """
    aliases: dict[str, str] = {}

    def add(alias: str, code: str) -> None:
        norm = alias.strip().lower()
        existing = aliases.get(norm)
        if existing is not None and existing != code:
            raise ValueError(f"alias collision: {norm!r} -> {existing} and {code}")
        aliases[norm] = code

    for row in rows:
        add(str(row["display_name"]), str(row["code"]))
    for alias, code in EXTRA_ALIASES:
        add(alias, code)
    return aliases


def seed_kpi_catalog(db: Session) -> bool:
    """Seed the KPI catalog release, rows, verified external codes, aliases and secondary domains.

    Idempotent at each layer. Returns True if the release was newly seeded, False if it already
    existed. The secondary-domain links are seeded by their own idempotent step in BOTH branches, so
    a later slice that adds the kpi_secondary_domain table to an already-seeded database still gets
    it populated.
    """
    if db.get(KpiCatalogRelease, CATALOG_VERSION) is not None:
        seed_secondary_domains(db)
        return False

    db.add(
        KpiCatalogRelease(
            version=CATALOG_VERSION,
            status=KpiReleaseStatus.ACTIVE,
            released_at=datetime.now(UTC),
            notes="Initial six-domain KPI catalog (ADR-0004).",
        )
    )
    db.flush()

    rows = kpi_rows()
    for row in rows:
        value_kind = row["value_kind"]
        unit = row["canonical_unit_ucum"]
        formula = row["formula_id"]
        db.add(
            KpiCatalog(
                code=str(row["code"]),
                display_name=str(row["display_name"]),
                primary_domain_axis=DomainAxis(str(row["primary_domain_axis"])),
                measurement_class=KpiMeasurementClass(str(row["measurement_class"])),
                value_kind=KpiValueKind(str(value_kind)) if value_kind is not None else None,
                canonical_unit_ucum=unit if isinstance(unit, str) else None,
                tier=KpiCatalogTier(str(row["tier"])),
                default_enabled=bool(row["default_enabled"]),
                is_derived=bool(row["is_derived"]),
                formula_id=formula if isinstance(formula, str) else None,
                clinician_visible=bool(row["clinician_visible"]),
                patient_visible=bool(row["patient_visible"]),
                status=KpiStatus.ACTIVE,
                introduced_in=CATALOG_VERSION,
            )
        )
    db.flush()

    for kpi_code, code_system, external_code, context in VERIFIED_EXTERNAL_CODES:
        db.add(
            KpiExternalCode(
                kpi_code=kpi_code,
                code_system=code_system,
                external_code=external_code,
                mapping_context={"note": context},
                verification_status=KpiExternalCodeStatus.VERIFIED,
                verified_at=datetime.now(UTC),
                verified_by="adr-0004-starter-set",
            )
        )

    for norm, code in _aliases_for(rows).items():
        db.add(KpiAlias(kpi_code=code, alias_normalized=norm))
    db.flush()
    seed_secondary_domains(db)
    return True


def seed_secondary_domains(db: Session) -> bool:
    """Seed kpi_secondary_domain links (ADR-0004 §4.2/§7, Slice 2). Own idempotent guard.

    Separate from the catalog-release guard above: this lets the table be populated when it is added
    to a database whose catalog rows already exist. Returns True if it seeded, False if links exist.
    """
    if db.execute(select(func.count()).select_from(KpiSecondaryDomain)).scalar_one():
        return False
    for kpi_code, axis in kpi_secondary_domain_rows():
        db.add(KpiSecondaryDomain(kpi_code=kpi_code, domain_axis=DomainAxis(axis)))
    db.flush()
    return True


def secondary_domains_for(db: Session, kpi_code: str) -> list[DomainAxis]:
    """The secondary domains linked to a KPI (navigational only; primary lives on KpiCatalog)."""
    rows = db.execute(
        select(KpiSecondaryDomain.domain_axis).where(KpiSecondaryDomain.kpi_code == kpi_code)
    ).scalars()
    return list(rows)


def kpi_codes_for_domain(db: Session, domain: DomainAxis) -> set[str]:
    """All KPI codes relevant to a domain: primary membership UNION secondary links.

    Membership only — it surfaces which biomarkers a domain view may show; it derives no verdict
    and merges no evidence across axes (ADR-0003).
    """
    primary = db.execute(
        select(KpiCatalog.code).where(KpiCatalog.primary_domain_axis == domain)
    ).scalars()
    secondary = db.execute(
        select(KpiSecondaryDomain.kpi_code).where(KpiSecondaryDomain.domain_axis == domain)
    ).scalars()
    return set(primary) | set(secondary)


def domain_membership(
    db: Session, kpi_codes: set[str]
) -> dict[str, tuple[DomainAxis, list[DomainAxis]]]:
    """Primary domain + secondary domains for each given KPI code (navigational membership only).

    Returns {kpi_code: (primary_domain, [secondary_domains])}. Two batched queries, no per-code
    round-trips. Used to label an observation's catalog domains; it derives no verdict (ADR-0003).
    """
    if not kpi_codes:
        return {}
    out: dict[str, tuple[DomainAxis, list[DomainAxis]]] = {}
    for code, primary in db.execute(
        select(KpiCatalog.code, KpiCatalog.primary_domain_axis).where(
            KpiCatalog.code.in_(kpi_codes)
        )
    ).all():
        out[code] = (primary, [])
    for code, axis in db.execute(
        select(KpiSecondaryDomain.kpi_code, KpiSecondaryDomain.domain_axis).where(
            KpiSecondaryDomain.kpi_code.in_(kpi_codes)
        )
    ).all():
        entry = out.get(code)
        if entry is not None:
            entry[1].append(axis)
    return out


def resolve_kpi_code(db: Session, source_name: str, loinc: str | None = None) -> str | None:
    """Resolve a source term (and optional verified LOINC) to a canonical KPI code, or None.

    Global alias first; then a VERIFIED external code. Never guesses.
    """
    norm = source_name.strip().lower()
    alias = db.execute(
        select(KpiAlias.kpi_code).where(
            KpiAlias.alias_normalized == norm, KpiAlias.source_system == ""
        )
    ).scalar_one_or_none()
    if alias is not None:
        return alias
    if loinc:
        ext = db.execute(
            select(KpiExternalCode.kpi_code).where(
                KpiExternalCode.external_code == loinc,
                KpiExternalCode.verification_status == KpiExternalCodeStatus.VERIFIED,
            )
        ).scalar_one_or_none()
        if ext is not None:
            return ext
    return None


# Read-time default comparison policy per measurement class (ADR-0004 Slice 3). The catalog's
# per-KPI comparison_policy is left NULL; a future signed-off slice may override per KPI. Only the
# classes whose §9 non-merge cases need recorded context require matching context — routine
# laboratory/vital/anthropometric/derived stay method_aware (compare on KPI + unit), so existing
# deltas (e.g. the LDL series) are unaffected.
_CLASS_DEFAULT_POLICY: dict[KpiMeasurementClass, KpiComparisonPolicy] = {
    KpiMeasurementClass.LABORATORY: KpiComparisonPolicy.METHOD_AWARE,
    KpiMeasurementClass.VITAL_SIGN: KpiComparisonPolicy.METHOD_AWARE,
    KpiMeasurementClass.ANTHROPOMETRIC: KpiComparisonPolicy.METHOD_AWARE,
    KpiMeasurementClass.BODY_COMPOSITION: KpiComparisonPolicy.SAME_DEVICE_ALGORITHM_REQUIRED,
    KpiMeasurementClass.FUNCTIONAL_TEST: KpiComparisonPolicy.SAME_INSTRUMENT_VERSION_REQUIRED,
    KpiMeasurementClass.WEARABLE: KpiComparisonPolicy.SAME_DEVICE_ALGORITHM_REQUIRED,
    KpiMeasurementClass.IMAGING: KpiComparisonPolicy.SAME_IMAGING_PROTOCOL_REQUIRED,
    KpiMeasurementClass.DERIVED: KpiComparisonPolicy.SAME_FORMULA_VERSION_REQUIRED,
    KpiMeasurementClass.OMICS: KpiComparisonPolicy.SAME_OMICS_PLATFORM_REQUIRED,
}


def policy_for_measurement_class(measurement_class: KpiMeasurementClass) -> KpiComparisonPolicy:
    """The conservative default longitudinal-comparison policy for a measurement class."""
    return _CLASS_DEFAULT_POLICY[measurement_class]


def resolve_comparison_policies(db: Session, kpi_codes: set[str]) -> dict[str, KpiComparisonPolicy]:
    """Resolve each KPI's effective comparison policy: the catalog value if set, else the
    measurement-class default. Batched. Codes not in the catalog are simply absent from the result.
    """
    if not kpi_codes:
        return {}
    out: dict[str, KpiComparisonPolicy] = {}
    for code, measurement_class, policy in db.execute(
        select(KpiCatalog.code, KpiCatalog.measurement_class, KpiCatalog.comparison_policy).where(
            KpiCatalog.code.in_(kpi_codes)
        )
    ).all():
        out[code] = policy or policy_for_measurement_class(measurement_class)
    return out
