"""Redis-backed fixed-window rate limiting (P-pre-1, docs/notes/0010).

Applied to the abuse-prone surfaces: login, the public patient-view token surface,
uploads, imports, invitations, data export, reading the audit trail, the preparation-time
metric, report drafting and report release. FAIL-CLOSED when Redis is unreachable — a
missing backend must not silently disable throttling (503, in every environment: the
local/CI stacks provide Redis, so an outage is a real misconfiguration, never an implicit
bypass).

The FIRST refusal of a window emits an audited `rate_limited` security event on an
independent transaction; the refusals after it in the same window do not. A client that
keeps hammering a limit is refused every time and recorded once per window — otherwise the
limit would bound what the client asked for and leave it writing one append-only row, on a
second database connection, per refused request.

The three token surfaces (the patient view, the two invitation redemptions) record a wrong
token under the clinic the request names — a caller without a session writing into a
clinic's append-only trail. The limit per client address does not bound that: a caller has
as many addresses as it can find. `refusal_recording` does, per clinic and surface, whatever
the address: the first refusals of a window are recorded one by one, then one entry says
that recording stops for the rest of the window. The requests are still answered — a clinic's
patients are never locked out by someone else's guessing.
"""

from __future__ import annotations

import uuid
from typing import Literal

import redis as redis_lib
from redis.exceptions import RedisError

from hadp_api.config import get_settings
from hadp_api.errors import ServiceUnavailable, TooManyRequests
from hadp_api.modules.audit.service import record_security_event

_client: redis_lib.Redis | None = None


def _get_client() -> redis_lib.Redis:
    global _client
    if _client is None:
        _client = redis_lib.Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2
        )
    return _client


def reset_client() -> None:
    """Drop the cached client (tests that switch Redis URLs)."""
    global _client
    _client = None


def _count(name: str, window_seconds: int) -> int:
    """Count one more call under `name` and say how many its window holds now."""
    try:
        client = _get_client()
        pipe = client.pipeline(transaction=True)
        pipe.incr(name)
        pipe.ttl(name)
        count, ttl = (int(value) for value in pipe.execute())
        # The window starts with the first call. A key WITHOUT an expiry (-1) is one whose
        # EXPIRE never arrived — a timeout or a crash between the two commands: left alone it
        # would count forever and refuse that caller for good, so it is given its window now.
        if count == 1 or ttl == -1:
            client.expire(name, window_seconds)
    except RedisError as exc:
        # Fail closed: no throttling backend, no throttled surface.
        raise ServiceUnavailable("rate limiting unavailable") from exc
    return count


def check_rate_limit(
    *,
    action: str,
    key: str,
    limit: int,
    window_seconds: int,
    correlation_id: str | None = None,
) -> None:
    """INCR-based fixed window: the (limit+1)-th call inside the window is refused (429)."""
    count = _count(f"rl:{action}:{key}", window_seconds)
    if count > limit:
        if count == limit + 1:
            record_security_event(
                action="rate_limited",
                correlation_id=correlation_id,
                detail={"action": action},
            )
        raise TooManyRequests("too many requests")


# What a clinic's trail takes from callers without a session, per surface and window.
REFUSALS_RECORDED = 30
REFUSAL_WINDOW_SECONDS = 60

RefusalRecording = Literal["each", "stops", "stopped"]


def refusal_recording(*, surface: str, tenant_id: uuid.UUID) -> RefusalRecording:
    """How the refusal just given on a token surface is recorded under the clinic it named.

    "each": as its own entry. "stops": by the one entry that says the refusals after it, in
    this window, are not recorded one by one. "stopped": not at all — that entry was written.
    Counted per clinic and surface, not per caller. The caller writes the entry: every audit
    write names its action where it is made (apps/api/tests/test_audit_read.py).
    """
    count = _count(f"rl-recorded:{surface}:{tenant_id}", REFUSAL_WINDOW_SECONDS)
    if count <= REFUSALS_RECORDED:
        return "each"
    return "stops" if count == REFUSALS_RECORDED + 1 else "stopped"
