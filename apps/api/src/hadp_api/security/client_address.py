"""Whose request it is, for the limits that count per client address.

A browser never reaches the API: the web server does, on the browser's behalf. The API's peer
is therefore the web server for every sign-in, every patient link and every invitation — a
limit counted on the peer is one budget for all of them, and one client can use it up for
everyone. So the web server passes on the `X-Forwarded-For` it received, and this module
decides which entry of it to believe:

- only when the peer is one of `TRUSTED_PROXIES` (the web server). From anyone else the
  header is the caller's own text and is not read.
- the entry `TRUSTED_PROXY_HOPS` from the right: what the last proxy in front of the web
  server saw. Everything further left is whatever the client chose to send.
- only if that entry is an address. A header that is too short, or holds something else at
  that position, is not believed.

Whenever the header is not believed the answer is the peer — today's shared budget, never a
value the caller picked. This module is the only reader of the header: the API server is
started with `--no-proxy-headers`, so that uvicorn does not rewrite the peer from the same
header before this code sees it (it would, for a peer on the loopback address).
"""

from __future__ import annotations

import ipaddress

from fastapi import Request

from hadp_api.config import get_settings, parse_trusted_proxies

_HEADER = "x-forwarded-for"
# An IPv6 client holds a whole /64 (and often more): counted per address, one client would
# have a fresh budget for each of 2**64 addresses.
_IPV6_BUCKET_PREFIX = 64


def client_address(request: Request) -> str:
    """The key under which this request counts against an address-keyed limit."""
    if request.client is None:
        return "unknown"
    peer = request.client.host
    settings = get_settings()
    forwarded = _forwarded_client(
        peer,
        request.headers.getlist(_HEADER),
        trusted=parse_trusted_proxies(settings.trusted_proxies),
        hops=settings.trusted_proxy_hops,
    )
    return _bucket(forwarded or peer)


def _forwarded_client(
    peer: str,
    header_values: list[str],
    *,
    trusted: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
    hops: int,
) -> str | None:
    """The client the peer names, or None when the peer is not believed or names none."""
    if not _is_trusted(peer, trusted):
        return None
    # A header sent more than once reads as one list, in order (RFC 9110 §5.3).
    chain = [entry.strip() for value in header_values for entry in value.split(",")]
    if len(chain) < hops:
        return None
    entry = chain[-hops]
    try:
        ipaddress.ip_address(entry)
    except ValueError:
        return None
    return entry


def _is_trusted(
    peer: str, trusted: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
) -> bool:
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        # Not an address (a test client's name, a socket path): nobody to trust.
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return any(address.version == network.version and address in network for network in trusted)


def _bucket(address: str) -> str:
    """One key per client: an IPv4 address as it is, an IPv6 address by its /64."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return address
    if isinstance(parsed, ipaddress.IPv4Address):
        return str(parsed)
    if parsed.ipv4_mapped is not None:
        return str(parsed.ipv4_mapped)
    return str(ipaddress.ip_network((int(parsed), _IPV6_BUCKET_PREFIX), strict=False))
