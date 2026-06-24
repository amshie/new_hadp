"""Forbidden-language scan over apps/web user-facing copy.

ADR-0004 §0 promises "DE/EN labels through the language scan before any UI ships", but no apps/web
copy scanner existed (only the narrative-provider scan in test_forbidden_language.py). This closes
that gap: it scans every .ts/.tsx under apps/web/src for restricted intended-use terms, using the
existing pytest runner (so `make check` / `make test-db` enforce it).

Guards against false positives: comments are stripped (a meta-comment naming a banned term must not
trip the scan); single words match on word boundaries (so "secure" != "cure", "optimalLayout" is not
"optimal"); and the only two sanctioned, doctrine-permitted disclaimers (which negate "diagnosis"/
"treatment") are stripped before matching. Any other use of a restricted term — even negated — is
flagged, exactly as the intended-use boundary requires.
"""

from __future__ import annotations

import re
from pathlib import Path

_WEB_SRC = Path(__file__).resolve().parents[2] / "web" / "src"

# Stems matched at a word START (a letter BEFORE disqualifies, so "secure" != "cure"; no trailing
# guard, so plurals and German inflections are caught: treatment(s), recommend(ed), optimal(en),
# disease(s), diagnos(e/is), prescrib(e)).
_STEMS = (
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
_PHRASES = ("risk score", "biological age")

# The ONLY sanctioned disclaimers (doctrine-permitted negations). Lowercase, whitespace-normalized;
# stripped before matching. Every other use of a restricted term — even negated — is still flagged.
_SANCTIONED = (
    "not a diagnosis or treatment advice",
    "keine automatische diagnose oder therapieempfehlung",
)

_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)


def _normalize(text: str) -> str:
    body = re.sub(r"\s+", " ", _COMMENT.sub(" ", text).lower())
    for phrase in _SANCTIONED:
        body = body.replace(phrase, " ")
    return body


def _violations(text: str) -> list[str]:
    body = _normalize(text)
    hits: list[str] = []
    hits += [s for s in _STEMS if re.search(rf"(?<![a-z]){re.escape(s)}", body)]
    hits += [p for p in _PHRASES if p in body]
    return sorted(set(hits))


def test_web_copy_has_no_forbidden_language() -> None:
    assert _WEB_SRC.is_dir(), f"web src not found: {_WEB_SRC}"
    files = sorted(_WEB_SRC.rglob("*.ts")) + sorted(_WEB_SRC.rglob("*.tsx"))
    assert files, "no web source files scanned"
    offenders = {
        str(path.relative_to(_WEB_SRC)): hits
        for path in files
        if (hits := _violations(path.read_text(encoding="utf-8")))
    }
    assert not offenders, f"forbidden intended-use language in web copy: {offenders}"
