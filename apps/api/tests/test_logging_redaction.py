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


def test_uvicorn_access_log_scrubs_query_tokens() -> None:
    """P-pre-3 (docs/notes/0010): the patient token travels as a ?token= query param;
    the access-log line must never carry it — while uvicorn's positional
    AccessFormatter (which unpacks record.args) keeps working."""
    from hadp_api.logging import configure_logging

    configure_logging()  # attaches ArgsRedactingFilter to the uvicorn.access logger
    access = logging.getLogger("uvicorn.access")
    # Pin the logger state: other tests/plugins may disable or level-filter it; the
    # subject under test is the FILTER, which runs regardless once the record flows.
    access.disabled = False
    access.setLevel(logging.INFO)
    # Snapshot inside emit(): logger handlers run BEFORE propagation, i.e. exactly
    # where uvicorn's own AccessFormatter sits (its access logger doesn't propagate);
    # the test-process root handler would mutate the shared record afterwards.
    captured: list[tuple[str, object]] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append((record.getMessage(), record.args))

    handler = _Capture()
    access.addHandler(handler)
    try:
        access.info(
            '%s - "%s %s HTTP/1.1" %d',
            "127.0.0.1:5000",
            "GET",
            "/api/v1/patient-view?tenant=70a6e3eb&token=synthetic-test-only-value",
            200,
        )
    finally:
        access.removeHandler(handler)
    assert captured, "access record was not captured"
    rendered, args = captured[0]
    # The args tuple SURVIVES (uvicorn's formatter unpacks it positionally) …
    assert isinstance(args, tuple) and len(args) == 4
    # … and the token is gone while the path stays diagnosable.
    assert "synthetic-test-only-value" not in rendered
    assert "patient-view" in rendered
