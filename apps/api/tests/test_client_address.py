"""Whose request it is, for the limits that count per client address.

The API's peer is the web server for every browser. Counted on the peer, sign-in, the patient
view and the two invitation redemptions each had one budget for everybody behind the web
server — one client could use it up for all. The web server now passes on the
`X-Forwarded-For` it received; these tests hold the rule by which the API believes it
(security/client_address.py): only from a peer named in TRUSTED_PROXIES, only the entry
TRUSTED_PROXY_HOPS from the right, only if it is an address — and otherwise the peer, never
a value the caller picked.

Addresses are the documentation ranges of RFC 5737 and RFC 3849; nobody's.
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import re
import uuid
from pathlib import Path

import pytest
import redis as redis_lib
from fastapi.testclient import TestClient

from hadp_api import main as main_module
from hadp_api.config import Settings, get_settings
from hadp_api.security.client_address import _bucket

_REPO = Path(__file__).resolve().parents[3]
_API_SRC = _REPO / "apps" / "api" / "src" / "hadp_api"
_WEB_API = _REPO / "apps" / "web" / "src" / "lib" / "api.ts"

WEB = "10.20.0.5"  # the web server, as the API sees it
STRANGER = "198.51.100.40"  # some other caller of the API
A = "203.0.113.7"
B = "203.0.113.8"
TENANT = str(uuid.uuid4())  # no such clinic: nothing reaches a trail


def _from(client, peer: str) -> TestClient:  # type: ignore[no-untyped-def]
    """A caller of the API whose connection comes from `peer`."""
    return TestClient(client.app, base_url=str(client.base_url), client=(peer, 50000))


def _guess(caller: TestClient, forwarded: str | list[str] | None = None) -> int:
    """One wrong token on the patient view; `forwarded` is the X-Forwarded-For sent with it."""
    values = [forwarded] if isinstance(forwarded, str) else (forwarded or [])
    resp = caller.post(
        "/api/v1/patient-view",
        json={"tenant": TENANT, "token": "guess"},
        headers=[("x-forwarded-for", value) for value in values],
    )
    return resp.status_code


def _counted() -> dict[str, int]:
    """What the limiter holds: the key each call was counted under, and how many."""
    store = redis_lib.Redis.from_url(get_settings().redis_url)
    return {key.decode(): int(store.get(key) or 0) for key in store.scan_iter(match="rl:*")}


# --- Who is believed --------------------------------------------------------------------


def test_each_client_the_web_server_names_has_its_own_budget(client, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    trust_proxies(WEB)
    web = _from(client, WEB)

    assert [_guess(web, A) for _ in range(30)] == [404] * 30
    assert _guess(web, A) == 429
    # Another client, the same web server: not refused for what the first one did.
    assert _guess(web, B) == 404
    assert _counted() == {f"rl:patient_view:{A}": 31, f"rl:patient_view:{B}": 1}


def test_what_the_client_wrote_into_the_header_itself_is_not_believed(
    client, trust_proxies
) -> None:  # type: ignore[no-untyped-def]
    """The proxy in front of the web server adds the address it saw at the right end;
    everything to the left arrived from the client."""
    trust_proxies(WEB)
    web = _from(client, WEB)
    for _ in range(30):
        _guess(web, A)

    # A, claiming to be B (and a third party), is still A.
    assert _guess(web, f"{B}, 198.51.100.99, {A}") == 429
    # B, with A's address written in front, is B.
    assert _guess(web, f"{A}, {B}") == 404


def test_a_caller_that_is_not_the_web_server_cannot_name_a_client(client, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    """From any other peer the header is the caller's own text."""
    trust_proxies(WEB)
    stranger = _from(client, STRANGER)

    answers = [_guess(stranger, f"203.0.113.{n}") for n in range(1, 32)]

    assert answers == [404] * 30 + [429]
    assert _counted() == {f"rl:patient_view:{STRANGER}": 31}


def test_nobody_is_believed_unless_configured(client) -> None:  # type: ignore[no-untyped-def]
    """The default: the header is never read, the peer is counted."""
    assert get_settings().trusted_proxies == ""
    web = _from(client, WEB)

    assert _guess(web, A) == 404
    assert _guess(web, B) == 404
    assert _counted() == {f"rl:patient_view:{WEB}": 2}


def test_a_trusted_peer_is_named_by_address_or_by_network(client, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    trust_proxies(" 192.0.2.1 , 10.20.0.0/24 ,")

    assert _guess(_from(client, "10.20.0.77"), A) == 404  # inside the network
    assert _guess(_from(client, "::ffff:10.20.0.78"), A) == 404  # the same, IPv4-mapped
    assert _guess(_from(client, "10.20.1.5"), B) == 404  # outside it
    assert _counted() == {f"rl:patient_view:{A}": 2, "rl:patient_view:10.20.1.5": 1}


# --- Which entry ------------------------------------------------------------------------


def test_the_entry_is_counted_from_the_right_by_the_number_of_proxies(
    client, trust_proxies
) -> None:  # type: ignore[no-untyped-def]
    """Two proxies in front of the web server (say a CDN, then a load balancer): the last
    entry is the CDN's address as the load balancer saw it, the one before it the client."""
    trust_proxies(WEB, hops=2)
    web = _from(client, WEB)

    assert _guess(web, f"{B}, {A}, 198.51.100.1") == 404
    assert _counted() == {f"rl:patient_view:{A}": 1}


def test_a_header_sent_twice_reads_as_one_list(client, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    trust_proxies(WEB)

    assert _guess(_from(client, WEB), [B, A]) == 404
    assert _counted() == {f"rl:patient_view:{A}": 1}


@pytest.mark.parametrize(
    ("hops", "forwarded"),
    [
        (1, None),  # no header at all
        (1, ""),
        (1, "unknown"),
        (1, f"{A}:4711"),  # an address with a port is not an address
        (1, f"{A}, "),  # the position that counts is empty
        (1, f"{A}, not-an-address"),
        (2, A),  # shorter than the number of proxies
        (2, f"not-an-address, {A}"),
    ],
)
def test_a_header_that_names_no_address_where_it_counts_leaves_the_peer(  # type: ignore[no-untyped-def]
    client, trust_proxies, hops: int, forwarded: str | None
) -> None:
    """Not believed means the shared budget of the peer — never the caller's choice."""
    trust_proxies(WEB, hops=hops)

    assert _guess(_from(client, WEB), forwarded) == 404
    assert _counted() == {f"rl:patient_view:{WEB}": 1}


# --- One key per client -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("address", "key"),
    [
        ("203.0.113.7", "203.0.113.7"),
        # An IPv6 client holds at least a /64: one budget for all of it.
        ("2001:db8:1:2::1", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff:ffff:ffff:9", "2001:db8:1:2::/64"),
        ("2001:db8:1:3::1", "2001:db8:1:3::/64"),
        ("::ffff:203.0.113.7", "203.0.113.7"),  # IPv4 through an IPv6 socket
        ("fe80::1%eth0", "fe80::/64"),
        ("testclient", "testclient"),  # not an address: as it is
    ],
)
def test_the_key_of_an_address(address: str, key: str) -> None:
    assert _bucket(address) == key


def test_the_addresses_of_one_ipv6_network_share_a_budget(client, trust_proxies) -> None:  # type: ignore[no-untyped-def]
    trust_proxies(WEB)
    web = _from(client, WEB)

    for address in ("2001:db8:1:2::1", "2001:db8:1:2:aaaa::2", "2001:db8:1:3::1"):
        assert _guess(web, address) == 404

    assert _counted() == {
        "rl:patient_view:2001:db8:1:2::/64": 2,
        "rl:patient_view:2001:db8:1:3::/64": 1,
    }


# --- Every limit that counts per address ------------------------------------------------

_NOBODY = {"display_name": "Synthetic Nobody", "email": "nobody@synthetic.example"}


@pytest.mark.parametrize(
    ("path", "body", "action"),
    [
        ("/api/v1/auth/dev-login", {"email": "ghost@synthetic.example"}, "auth.dev_login"),
        ("/api/v1/patient-view", {"tenant": TENANT, "token": "guess"}, "patient_view"),
        ("/api/v1/invitations/redeem", {"tenant": TENANT, "token": "guess"}, "invitation.redeem"),
        (
            "/api/v1/staff-invitations/redeem",
            {"tenant": TENANT, "token": "guess", **_NOBODY},
            "staff_invite.redeem",
        ),
    ],
)
def test_every_address_keyed_limit_counts_the_client(  # type: ignore[no-untyped-def]
    client, trust_proxies, path: str, body: dict[str, str], action: str
) -> None:
    trust_proxies(WEB)

    resp = _from(client, WEB).post(path, json=body, headers={"x-forwarded-for": A})

    assert resp.status_code in (401, 404), resp.text
    assert _counted() == {f"rl:{action}:{A}": 1}


def _address_keyed_routes() -> set[str]:
    """The paths of the handlers that count per client address, read from the source."""
    paths: set[str] = set()
    for module in sorted((_API_SRC / "api").glob("*.py")):
        tree = ast.parse(module.read_text())
        prefix = ""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "APIRouter":
                for keyword in node.keywords:
                    if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                        prefix = str(keyword.value.value)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            calls = {
                getattr(call.func, "id", None)
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
            }
            if "client_address" not in calls:
                continue
            for decorator in node.decorator_list:
                assert isinstance(decorator, ast.Call), f"{module.name}:{node.name}"
                route = decorator.args[0]
                assert isinstance(route, ast.Constant), f"{module.name}:{node.name}"
                paths.add(f"/api/v1{prefix}{route.value}")
    return paths


def test_the_web_server_passes_the_address_on_for_exactly_those_calls() -> None:
    """A limit that counts per address needs the address from the web server — and no other
    call of the API is told where a request came from."""
    routes = _address_keyed_routes()
    assert routes == {
        "/api/v1/auth/dev-login",
        "/api/v1/patient-view",
        "/api/v1/invitations/redeem",
        "/api/v1/staff-invitations/redeem",
    }
    source = _WEB_API.read_text()
    for path in sorted(routes):
        assert source.count(path) == 1, f"{path}: called from more than one place in api.ts"
        # From the path to the end of that call (either way the formatter closes it).
        call = re.split(r"\}\);|\n  \);", source[source.index(path) :], maxsplit=1)[0]
        assert "forClient: true" in call or "await forwardedFor()" in call, (
            f"{path} counts per client address, and the web server does not pass it on"
        )
    passed_on = source.count("forClient: true") + source.count("...(await forwardedFor())")
    assert passed_on == len(routes)


# --- One reader of the header -----------------------------------------------------------


def test_every_start_of_the_api_server_leaves_the_header_to_the_api() -> None:
    """uvicorn rewrites the peer from X-Forwarded-For for a peer it trusts (the loopback
    address, by default) — before this code sees the request, and by another rule."""
    starts = {
        "apps/api/Dockerfile": [
            line
            for line in (_REPO / "apps/api/Dockerfile").read_text().splitlines()
            if line.startswith(("CMD", "ENTRYPOINT"))
        ],
        "Makefile": [
            line
            for line in (_REPO / "Makefile").read_text().splitlines()
            if "uvicorn hadp_api.main:app" in line
        ],
        ".github/workflows/ci.yml": [
            line
            for line in (_REPO / ".github/workflows/ci.yml").read_text().splitlines()
            if "uvicorn hadp_api.main:app" in line
        ],
        ".claude/launch.json": [
            " ".join(configuration["runtimeArgs"])
            for configuration in json.loads((_REPO / ".claude/launch.json").read_text())[
                "configurations"
            ]
            if "uvicorn" in configuration["runtimeArgs"]
        ],
    }
    for where, lines in starts.items():
        assert lines, f"{where}: no start of the API server found"
        for line in lines:
            assert re.search(r"--no-proxy-headers\b", line), f"{where}: {line.strip()}"


# --- Said at start ----------------------------------------------------------------------


def _production(**overrides: object) -> Settings:
    return Settings(  # type: ignore[arg-type]
        **{
            "app_env": "production",
            "database_url": "postgresql+psycopg://postgres:postgres@db:5432/hadp",
            "app_database_url": "postgresql+psycopg://hadp_app:hadp_app@db:5432/hadp",
            "session_secret": "x" * 40,
            "s3_access_key_id": "synthetic-key",
            "s3_secret_access_key": "synthetic-secret",
            "session_cookie_name": "__Host-hadp_session",
            "csrf_cookie_name": "__Host-hadp_csrf",
            **overrides,
        }
    )


def _said_at_start(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, settings: Settings
) -> list[logging.LogRecord]:
    """Start the application as configured by `settings`; what it logged about the limits."""
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    async def start() -> None:
        async with main_module._lifespan(main_module.app):
            pass

    with caplog.at_level(logging.INFO, logger="hadp_api.main"):
        asyncio.run(start())
    return [r for r in caplog.records if r.name == "hadp_api.main" and "limits" in r.getMessage()]


def test_a_production_api_that_believes_no_peer_warns_when_it_starts(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Unset, every client behind the web server shares one budget — and nothing else shows
    it: no request fails, no check refuses."""
    (said,) = _said_at_start(monkeypatch, caplog, _production())

    assert said.levelno == logging.WARNING
    assert "TRUSTED_PROXIES is not set" in said.getMessage()


def test_outside_production_the_same_is_said_without_a_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    (said,) = _said_at_start(monkeypatch, caplog, Settings(app_env="development"))

    assert said.levelno == logging.INFO
    assert "TRUSTED_PROXIES is not set" in said.getMessage()


def test_an_api_that_believes_a_peer_says_how_many_and_not_which(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    settings = _production(trusted_proxies=f"{WEB}, 10.30.0.0/24", trusted_proxy_hops=2)

    (said,) = _said_at_start(monkeypatch, caplog, settings)

    assert said.levelno == logging.INFO
    assert "trusted networks=2, hops=2" in said.getMessage()
    assert WEB not in said.getMessage() and "10.30" not in said.getMessage()
