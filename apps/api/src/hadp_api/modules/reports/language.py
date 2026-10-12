"""Intended-use language guard for human-edited report text.

The deterministic provider's output is guarded by tests, but an edit is free text bound for a
patient-facing report — so the restricted intended-use terms (docs/regulatory/INTENDED_USE.md
"Vocabulary") are enforced at write time, not only by review. This is the single source for
the stems the apps/web copy scan (tests/test_web_copy_language.py) matches too.

Any change to these terms is an intended-use boundary change (documented review process),
never an engineering convenience.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Stems matched at a word START (a letter BEFORE disqualifies, so "secure" != "cure"; no
# trailing guard, so plurals and German inflections are caught: Diagnose(n), optimal(e)).
RESTRICTED_STEMS = (
    "diagnos",
    "prescrib",
    "treatment",
    "medication",
    "supplement",
    "optimal",
    "disease",
    "recommend",
    "cure",
    "abnormal",
)
# Distinctive phrases (plain substring).
RESTRICTED_PHRASES = ("risk score", "biological age")


def restricted_terms(texts: Iterable[str]) -> list[str]:
    """Return the restricted terms found in the given texts (sorted, de-duplicated)."""
    body = re.sub(r"\s+", " ", " ".join(texts).lower())
    hits = [s for s in RESTRICTED_STEMS if re.search(rf"(?<![a-z]){re.escape(s)}", body)]
    hits += [p for p in RESTRICTED_PHRASES if p in body]
    return sorted(set(hits))
