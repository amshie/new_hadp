"""What the catalog says about the KPI a source name resolved to (ADR-0004 §13).

Kept apart from the ORM so the normalizer can depend on it without a database.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogTerm:
    """The KPI an alias names, and the unit its values are held in. What a name MAY mean —
    not a statement that a value under it may be acted on without a human: that is decided
    where values are imported (`modules/imports/normalize.py`)."""

    kpi_code: str
    canonical_unit: str | None
