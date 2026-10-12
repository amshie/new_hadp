"""What the catalog says about the KPI a source name resolved to (ADR-0004 §13).

Kept apart from the ORM so the normalizer can depend on it without a database.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogTerm:
    kpi_code: str
    canonical_unit: str | None
    # A value of this KPI may be normalized by the import alone. False for a KPI whose values
    # only compare with recorded measurement context (device, instrument, protocol, formula):
    # a file or a typed row carries none of that, so a human looks first.
    automatic: bool
