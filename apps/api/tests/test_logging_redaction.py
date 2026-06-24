"""Health-data redaction in logs is implemented, not merely promised."""

from __future__ import annotations

import logging

from hadp_api.logging import RedactingFilter, redact


def test_redact_removes_emails_tokens_values() -> None:
    text = "patient jane@example.com value 12.7 token=abc123secret password: hunter2"
    out = redact(text)
    assert "jane@example.com" not in out
    assert "abc123secret" not in out
    assert "hunter2" not in out
    assert "12.7" not in out  # long-ish numeric run treated as a possible value


def test_redacting_filter_scrubs_log_record(caplog) -> None:  # type: ignore[no-untyped-def]
    logger = logging.getLogger("hadp_test.redaction")
    logger.addFilter(RedactingFilter())
    with caplog.at_level(logging.INFO, logger="hadp_test.redaction"):
        logger.info("login for user %s with token %s", "secret@example.com", "tok_abcdef123456")
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    assert "secret@example.com" not in rendered
    assert "tok_abcdef123456" not in rendered
