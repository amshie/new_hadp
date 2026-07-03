"""Browserless route smoke against a running web app + API.

Verifies the governed web surfaces over real HTTP on seeded synthetic data:
unauthenticated requests are pushed to /login, the retired /worklist redirects to
/overview, unknown routes render the neutral 404, and an authenticated session
renders the real dashboard with the synthetic-data banner. Requires the API on
:8000 (dev mode) and the web app on :3000 against a seeded dev DB. Synthetic data
only. Exits non-zero on any failure. (Full Playwright e2e is a later slice.)
"""

from __future__ import annotations

import os
import sys

import httpx

WEB = os.environ.get("WEB_SMOKE_BASE", "http://127.0.0.1:3000")
API = os.environ.get("API_SMOKE_BASE", "http://127.0.0.1:8000/api/v1")
REDIRECT = {301, 302, 303, 307, 308}


def main() -> int:
    # Unauthenticated: deny-by-default guards + retired-route redirect + 404 boundary.
    with httpx.Client(base_url=WEB, timeout=60.0, follow_redirects=False) as web:
        r = web.get("/login")
        assert r.status_code == 200, ("/login", r.status_code)
        assert "Klinischer Zugang" in r.text, "/login did not render the sign-in card"

        for path in ("/", "/overview"):
            r = web.get(path)
            assert r.status_code in REDIRECT, (path, r.status_code)
            assert "/login" in r.headers["location"], (path, r.headers["location"])

        r = web.get("/worklist")
        assert r.status_code in REDIRECT, ("/worklist", r.status_code)
        assert "/overview" in r.headers["location"], r.headers["location"]

        r = web.get("/this-route-does-not-exist")
        assert r.status_code == 404, ("unknown route", r.status_code)
        assert "Seite nicht gefunden" in r.text, "not-found boundary did not render"

    # Real session via the API (same path the login action uses), then authed pages.
    with httpx.Client(base_url=API, timeout=60.0) as api:
        r = api.post("/auth/dev-login", json={"email": "clinician@demo.synthetic"})
        assert r.status_code == 200, ("dev-login", r.status_code, r.text)
        tenants = api.get("/tenancy/my-tenants").json()
        tenant = next(t for t in tenants if t["tenant_slug"] == "demo-clinic")
        r = api.post("/tenancy/select-tenant", json={"tenant_id": tenant["tenant_id"]})
        assert r.status_code == 200, ("select-tenant", r.status_code)
        session = api.cookies.get("hadp_session")
        assert session, "dev-login issued no hadp_session cookie"
        patients = api.get("/patients").json()
        pid = next(p for p in patients if p["external_ref"] == "SYN-0001")["id"]

    with httpx.Client(
        base_url=WEB,
        timeout=60.0,
        follow_redirects=False,
        cookies={"hadp_session": session},
    ) as web:
        r = web.get("/overview")
        assert r.status_code == 200, ("/overview authed", r.status_code)
        assert "Synthetische Beispieldaten" in r.text, "synthetic banner missing on /overview"

        r = web.get("/patients")
        assert r.status_code == 200, ("/patients authed", r.status_code)

        r = web.get(f"/patients/{pid}")
        assert r.status_code == 200, ("/patients/[id] authed", r.status_code)

    print("WEB SMOKE OK: guards, redirects, 404 boundary, and authed dashboard render")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - smoke script: report and fail
        print(f"WEB SMOKE FAILED: {exc!r}")
        sys.exit(1)
