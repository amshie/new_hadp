"""Redis-backed fixed-window rate limiting (P-pre-1, docs/notes/0010).

Applied to the abuse-prone surfaces: login, the public patient-view token surface,
uploads, imports, invitations, data export, reading the audit trail, report drafting and
report release. FAIL-CLOSED when Redis is unreachable — a missing backend must not silently
disable throttling (503, in every environment: the local/CI stacks provide Redis, so an
outage is a real misconfiguration, never an implicit bypass).

The FIRST refusal of a window emits an audited `rate_limited` security event on an
independent transaction; the refusals after it in the same window do not. A client that
keeps hammering a limit is refused every time and recorded once per window — otherwise the
limit would bound what the client asked for and leave it writing one append-only row, on a
second database connection, per refused request.
"""

from __future__ import annotations

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


def check_rate_limit(
    *,
    action: str,
    key: str,
    limit: int,
    window_seconds: int,
    correlation_id: str | None = None,
) -> None:
    """INCR-based fixed window: the (limit+1)-th call inside the window is refused (429)."""
    name = f"rl:{action}:{key}"
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
    if count > limit:
        if count == limit + 1:
            record_security_event(
                action="rate_limited",
                correlation_id=correlation_id,
                detail={"action": action},
            )
        raise TooManyRequests("too many requests")
