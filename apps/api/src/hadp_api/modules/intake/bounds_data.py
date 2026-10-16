"""Signed plausibility bounds per KPI — the single source of truth for `kpi_plausibility_bounds`.

EMPTY BY DESIGN. A hard bound ("a reading outside this cannot come from a living person") and a
delta threshold ("a change beyond this asks a human to look") are clinical statements. One is
added here only with its source and the clinician who signed it, after the register row for
the intake agent has been signed off (docs/regulatory/CLASSIFICATION_REGISTER.md). Until then
every mapped value is yellow with `plausibility_not_configured`: a human looks at each one.

Each entry: (kpi_code, unit, hard_low, hard_high, delta_max_relative, source, signed_by,
signed_at ISO date). The unit must be the KPI's canonical unit; the seed checks it.
"""

from __future__ import annotations

BOUNDS_VERSION = "bounds-0"

SIGNED_BOUNDS: list[tuple[str, str, str | None, str | None, str | None, str, str, str]] = []
