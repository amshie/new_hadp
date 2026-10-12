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
import re
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

        for path in ("/", "/overview", "/review-queue"):
            r = web.get(path)
            assert r.status_code in REDIRECT, (path, r.status_code)
            assert "/login" in r.headers["location"], (path, r.headers["location"])

        r = web.get("/worklist")
        assert r.status_code in REDIRECT, ("/worklist", r.status_code)
        assert "/overview" in r.headers["location"], r.headers["location"]

        r = web.get("/this-route-does-not-exist")
        assert r.status_code == 404, ("unknown route", r.status_code)
        assert "Seite nicht gefunden" in r.text, "not-found boundary did not render"

        # Patient-facing pages: neutral fail states + the four-part disclaimer, no fetch
        # on a malformed link (UUID guard), German copy.
        r = web.get("/einladung?tenant=not-a-uuid&token=x")
        assert r.status_code == 200, ("/einladung guard", r.status_code)
        assert "nicht oder nicht mehr gültig" in r.text
        assert "Pilotumgebung" in r.text, "disclaimer missing on /einladung"

        r = web.get("/patient-view")
        assert r.status_code == 200, ("/patient-view neutral", r.status_code)
        assert "nicht oder nicht mehr gültig" in r.text
        assert "Pilotumgebung" in r.text, "disclaimer missing on /patient-view"

        # Cookie-exchange entry: the token-bearing link 303-redirects to a clean,
        # tokenless /patient-view and stashes the credential in an httpOnly cookie, so the
        # bearer token never lands in the address bar or browser history.
        oeffnen = "/patient-view/oeffnen?tenant=00000000-0000-0000-0000-000000000000&token=synthetic-smoke"
        r = web.get(oeffnen)
        assert r.status_code in REDIRECT, ("/patient-view/oeffnen", r.status_code)
        loc = r.headers["location"]
        assert loc.endswith("/patient-view"), ("oeffnen redirect target", loc)
        assert "synthetic-smoke" not in loc, "token leaked into the redirect URL"
        set_cookie = "; ".join(r.headers.get_list("set-cookie"))
        assert "hadp_pv=" in set_cookie and "HttpOnly" in set_cookie, (
            "pv cookie not set httpOnly",
            set_cookie,
        )

    # Real session via the API (same path the login action uses), then authed pages.
    with httpx.Client(base_url=API, timeout=60.0) as api:
        r = api.post("/auth/dev-login", json={"email": "clinician@demo.synthetic"})
        assert r.status_code == 200, ("dev-login", r.status_code, r.text)
        # Double-submit CSRF (P-pre-2): unsafe calls carry the token issued at login.
        api.headers["x-csrf-token"] = api.cookies.get("hadp_csrf") or ""
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
        # The seeded patient has a report: the detail page must link to its review surface
        # (the only place approve/release live), and that link must resolve.
        review = re.search(rf'href="(/patients/{pid}/assessments/[0-9a-f-]{{36}})"', r.text)
        assert review, "patient detail does not link to the report review page"
        r = web.get(review.group(1))
        assert r.status_code == 200, ("review page via detail link", r.status_code)
        assert f'href="/patients/{pid}"' in r.text, "review page has no way back to the patient"

        r = web.get("/review-queue")
        assert r.status_code == 200, ("/review-queue authed", r.status_code)
        assert "Review-Queue" in r.text, "review queue page did not render"

        r = web.get(f"/patients/{pid}/interpretation/neu")
        assert r.status_code == 200, ("/interpretation/neu authed", r.status_code)
        assert "Korrektur-Run erfassen" in r.text or "Interpretation erfassen" in r.text

    print("WEB SMOKE OK: guards, redirects, 404 boundary, and authed dashboard render")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - smoke script: report and fail
        print(f"WEB SMOKE FAILED: {exc!r}")
        sys.exit(1)
