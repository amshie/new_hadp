"""Redis-backed fixed-window rate limiting (P-pre-1, docs/notes/0010).

Applied to the abuse-prone surfaces: login, the public patient-view token surface,
uploads, and report release. FAIL-CLOSED when Redis is unreachable — a missing backend
must not silently disable throttling (503, in every environment: the local/CI stacks
provide Redis, so an outage is a real misconfiguration, never an implicit bypass).
A breach emits an audited `rate_limited` security event on an independent transaction.
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
        count = int(client.incr(name))
        if count == 1:
            client.expire(name, window_seconds)
    except RedisError as exc:
        # Fail closed: no throttling backend, no throttled surface.
        raise ServiceUnavailable("rate limiting unavailable") from exc
    if count > limit:
        record_security_event(
            action="rate_limited",
            correlation_id=correlation_id,
            detail={"action": action},
        )
        raise TooManyRequests("too many requests")
