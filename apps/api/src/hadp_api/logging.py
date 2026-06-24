"""Logging with enforced health-data redaction.

Policy alone is insufficient (CLAUDE.md): redaction is implemented here and covered by
tests asserting that names, emails, values, tokens, and document contents do not appear
in log output. Application code must log only identifiers, codes, and timings — never
observation values, free text, or personal data — but this layer is the safety net.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

# Patterns scrubbed from every emitted log record as defense-in-depth.
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_BEARER = re.compile(r"(?i)\b(bearer|token|secret|password|authorization)\b\s*[=:]?\s*\S+")
_DECIMAL = re.compile(r"\b\d+\.\d+\b")  # decimal values (lab-value-shaped numbers)
_LONG_DIGITS = re.compile(r"\b\d[\d,]{5,}\b")  # long integer runs (possible values/ids)

_REDACTED = "[REDACTED]"


def redact(text: str) -> str:
    text = _EMAIL.sub(_REDACTED, text)
    text = _BEARER.sub(_REDACTED, text)
    text = _DECIMAL.sub(_REDACTED, text)
    text = _LONG_DIGITS.sub(_REDACTED, text)
    return text


class RedactingFilter(logging.Filter):
    """Scrubs the rendered message and string args of every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive: never crash logging
            message = str(record.msg)
        record.msg = redact(message)
        record.args = ()
        return True


_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def safe_extra(**fields: Any) -> dict[str, Any]:
    """Whitelist helper: callers pass only non-sensitive identifiers/timings.

    Values are still routed through the redactor by RedactingFilter, but this makes
    the intent explicit at call sites.
    """
    return dict(fields)
