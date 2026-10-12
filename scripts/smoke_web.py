"""Browserless route smoke against a running web app + API.

Verifies the governed web surfaces over real HTTP on seeded synthetic data:
unauthenticated requests are pushed to /login, the retired /worklist redirects to
/overview, unknown routes render the neutral 404, and an authenticated session
renders the real dashboard with the synthetic-data banner. Requires the API on
:8000 (dev mode) and the web app on :3000 against a seeded dev DB. Synthetic data
only. Exits non-zero on any failure. (Full Playwright e2e is a later slice.)

No page may carry mock UI (a password or second-factor field that checks nothing,
"Prototyp" wording, a notification control with nothing behind it), and the report
review page must state the version's real release status. With WEB_SMOKE_RELEASE=1
(CI) the seeded report is additionally approved and released through the API, so
the released wording is checked too; without it the report is left as it is.
"""

from __future__ import annotations

import os
import re
import sys

import httpx

WEB = os.environ.get("WEB_SMOKE_BASE", "http://127.0.0.1:3000")
API = os.environ.get("API_SMOKE_BASE", "http://127.0.0.1:8000/api/v1")
REDIRECT = {301, 302, 303, 307, 308}
EXERCISE_RELEASE = os.environ.get("WEB_SMOKE_RELEASE") == "1"

# The headline the review page shows above a report version, by lifecycle status.
STAGE_HEADLINE = {
    "draft_generated": "Systementwurf – nicht freigegeben.",
    "draft_edited": "Überarbeiteter Entwurf – nicht freigegeben.",
    "approved": "Klinisch genehmigt – noch nicht freigegeben.",
    "released": "Ärztlich freigegeben.",
    "rejected": "Zurückgewiesen – nicht freigegeben.",
}


# German "Prototyp…" wording only: a dev-mode page also embeds JavaScript source, where
# identifiers such as "ObjectSetPrototypeOf" are not copy.
MOCK_UI = (r"\bPrototyp(?!e)", "Benachrichtigungen", 'type="password"', 'href="#"')


def assert_no_mock_ui(path: str, html: str) -> None:
    """Nothing on a page pretends: no prototype wording, no control without a function."""
    for marker in MOCK_UI:
        assert not re.search(marker, html), f"{path} still carries mock UI: {marker!r}"


def assert_stage(path: str, html: str, report: dict) -> None:
    """The page says where the version stands — never "nicht freigegeben" once released."""
    status = report["status"]
    headline = STAGE_HEADLINE[status]
    if status == "draft_generated" and report.get("edited"):
        headline = STAGE_HEADLINE["draft_edited"]
    assert headline in html, (path, status, "status headline missing")
    if status == "released":
        assert "nicht freigegeben" not in html.lower(), (
            f"{path}: a released report is labelled as not released"
        )


def staff_session(email: str) -> httpx.Client:
    """An API session for a seeded synthetic account, scoped to the demo clinic."""
    api = httpx.Client(base_url=API, timeout=60.0)
    r = api.post("/auth/dev-login", json={"email": email})
    assert r.status_code == 200, ("dev-login", email, r.status_code, r.text)
    # Double-submit CSRF (P-pre-2): unsafe calls carry the token issued at login.
    api.headers["x-csrf-token"] = api.cookies.get("hadp_csrf") or ""
    tenants = api.get("/tenancy/my-tenants").json()
    tenant = next(t for t in tenants if t["tenant_slug"] == "demo-clinic")
    r = api.post("/tenancy/select-tenant", json={"tenant_id": tenant["tenant_id"]})
    assert r.status_code == 200, ("select-tenant", email, r.status_code)
    return api


def main() -> int:
    # Unauthenticated: deny-by-default guards + retired-route redirect + 404 boundary.
    with httpx.Client(base_url=WEB, timeout=60.0, follow_redirects=False) as web:
        r = web.get("/login")
        assert r.status_code == 200, ("/login", r.status_code)
        assert "Klinischer Zugang" in r.text, "/login did not render the sign-in card"
        # The development sign-in asks for an account's e-mail address and nothing else.
        assert 'name="email"' in r.text, "/login offers no sign-in form in dev mode"
        assert "Zwei-Faktor" not in r.text, "/login still shows a second-factor step"
        assert_no_mock_ui("/login", r.text)

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
    api = staff_session("clinician@demo.synthetic")
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
        assert_no_mock_ui("/overview", r.text)
        # Every navigation entry leads somewhere: the four real destinations, nothing else.
        for label in ("Übersicht", "Patienten", "Review-Queue", "Einstellungen"):
            assert label in r.text, f"navigation entry missing: {label}"
        assert "Audit-Protokoll" not in r.text, "navigation still lists a view that does not exist"

        r = web.get("/patients")
        assert r.status_code == 200, ("/patients authed", r.status_code)
        assert_no_mock_ui("/patients", r.text)

        r = web.get(f"/patients/{pid}")
        assert r.status_code == 200, ("/patients/[id] authed", r.status_code)
        assert_no_mock_ui("/patients/[id]", r.text)
        # The seeded patient has a report: the detail page must link to its review surface
        # (the only place approve/release live), and that link must resolve.
        review = re.search(rf'href="(/patients/{pid}/assessments/[0-9a-f-]{{36}})"', r.text)
        assert review, "patient detail does not link to the report review page"
        # Laboratory file intake lives on the patient page (care staff): the card and its
        # file field must render.
        assert "Labordaten" in r.text, "patient detail has no laboratory-files card"
        assert 'type="file"' in r.text, "laboratory-files card has no upload field"
        # Consent state per purpose is shown on the patient page (all staff).
        assert "Einwilligungen" in r.text, "patient detail has no consent card"
        assert "Freigabe geprüfter Berichte" in r.text, "consent card lists no purposes"
        # The data export is tenant administration (owner): this clinician session sees no card.
        assert "Datenauskunft erstellen" not in r.text, "data-export card shown to a non-owner"
        review_path = review.group(1)
        report_id = review_path.rsplit("/", 1)[1]
        r = web.get(review_path)
        assert r.status_code == 200, ("review page via detail link", r.status_code)
        assert f'href="/patients/{pid}"' in r.text, "review page has no way back to the patient"
        assert_no_mock_ui("review page", r.text)
        # The legacy shell's navigation leads to the real pages (it used to be dead links).
        for target in ("/overview", "/patients", "/review-queue", "/einstellungen"):
            assert f'href="{target}"' in r.text, f"review page navigation lacks {target}"
        report = api.get(f"/reports/{report_id}").json()
        assert_stage("review page", r.text, report)
        checked = [report["status"]]

        if EXERCISE_RELEASE:
            # Two-tier gate through the API (clinician approves, medical director releases),
            # then the same page must say "freigegeben" — and nowhere "nicht freigegeben".
            if report["status"] in ("draft_generated", "draft_edited"):
                r = api.post(f"/reports/{report_id}/approve")
                assert r.status_code == 200, ("approve", r.status_code, r.text)
                page = web.get(review_path).text
                approved = api.get(f"/reports/{report_id}").json()
                assert approved["status"] == "approved", approved["status"]
                assert_stage("review page (approved)", page, approved)
                checked.append("approved")
            if api.get(f"/reports/{report_id}").json()["status"] == "approved":
                director = staff_session("medical.director@demo.synthetic")
                try:
                    r = director.post(f"/reports/{report_id}/release")
                    assert r.status_code == 200, ("release", r.status_code, r.text)
                finally:
                    director.close()
            released = api.get(f"/reports/{report_id}").json()
            assert released["status"] == "released", ("release exercise", released["status"])
            assert_stage("review page (released)", web.get(review_path).text, released)
            checked.append("released")

        r = web.get("/review-queue")
        assert r.status_code == 200, ("/review-queue authed", r.status_code)
        assert "Review-Queue" in r.text, "review queue page did not render"
        assert_no_mock_ui("/review-queue", r.text)

        r = web.get(f"/patients/{pid}/interpretation/neu")
        assert r.status_code == 200, ("/interpretation/neu authed", r.status_code)
        assert "Korrektur-Run erfassen" in r.text or "Interpretation erfassen" in r.text
        assert_no_mock_ui("/interpretation/neu", r.text)

    api.close()
    print("WEB SMOKE OK: guards, redirects, 404 boundary, and authed dashboard render")
    print(f"  report status wording checked for: {', '.join(checked)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - smoke script: report and fail
        print(f"WEB SMOKE FAILED: {exc!r}")
        sys.exit(1)
