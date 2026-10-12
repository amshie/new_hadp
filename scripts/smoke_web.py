"""Browserless route smoke against a running web app + API.

Verifies the governed web surfaces over real HTTP on seeded synthetic data:
unauthenticated requests are pushed to /login, the retired /worklist redirects to
/overview, unknown routes render the neutral 404, and an authenticated session
renders the real dashboard with the synthetic-data banner. Requires the API on
:8000 (dev mode) and the web app on :3000 against a seeded dev DB. Synthetic data
only. Exits non-zero on any failure. (The clinic workflow itself is walked in a browser
by the Playwright suite in apps/web/e2e — `make test-e2e`.)

No page may carry mock UI (a password or second-factor field that checks nothing,
"Prototyp" wording, a notification control with nothing behind it), and the report
review page must state the version's real release status. With WEB_SMOKE_RELEASE=1
(CI) the seeded report is additionally approved and released through the API and the
patient view is opened with the issued link, and a second report is rejected and
reworked — so the wording is checked in every status. Without the variable nothing
is changed.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

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


# German "Prototyp / Prototyps / Prototypen / Prototyp-…" wording only: a dev-mode page also
# embeds JavaScript source, where "ObjectSetPrototypeOf" or "Prototype" is not copy.
MOCK_UI = (
    r"\bPrototyp(?:s|en)?(?![A-Za-z])",
    'aria-label="Benachrichtigungen"',
    'type="password"',
    'href="#"',
)
NAV_TARGETS = ["/overview", "/patients", "/review-queue", "/einstellungen"]
DRAFT_HEADLINES = ("Systementwurf", "Überarbeiteter Entwurf")


def assert_no_mock_ui(path: str, html: str) -> None:
    """Nothing on a page pretends: no prototype wording, no control without a function."""
    for marker in MOCK_UI:
        assert not re.search(marker, html), f"{path} still carries mock UI: {marker!r}"


def assert_nav(path: str, html: str, link_class: str) -> None:
    """The navigation is exactly the four pages that exist, each a real link."""
    hrefs = re.findall(rf'<a[^>]*class="{link_class}"[^>]*href="([^"]*)"', html)
    hrefs += re.findall(rf'<a[^>]*href="([^"]*)"[^>]*class="{link_class}"', html)
    assert sorted(set(hrefs)) == sorted(NAV_TARGETS), (
        path,
        "navigation entries",
        hrefs,
    )


def assert_stage(path: str, html: str, report: dict) -> None:
    """The page says where the version stands — and nothing that belongs to another status."""
    status = report["status"]
    headline = STAGE_HEADLINE[status]
    if status == "draft_generated" and report.get("edited"):
        headline = STAGE_HEADLINE["draft_edited"]
    assert headline in html, (path, status, "status headline missing")
    for other in set(STAGE_HEADLINE.values()) - {headline}:
        assert other not in html, (path, status, f"also shows {other!r}")
    if not status.startswith("draft"):
        for word in DRAFT_HEADLINES:
            assert word not in html, f"{path}: a {status} version is called a draft"
    if status == "released":
        assert "nicht freigegeben" not in html.lower(), (
            f"{path}: a released report is labelled as not released"
        )
        # A released status does not prove access: the wording must not claim she sees it.
        assert "sieht ausschließlich" not in html, f"{path}: claims the patient sees the report"
    if status == "rejected":
        # Rejected before or after the clinical approval — the status does not say which.
        assert "Signiert" not in html, f"{path}: a rejected version is shown as signed"


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
        assert_nav("/overview", r.text, "vb-nav")

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
        assert_nav("review page", r.text, "nav-link")
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
                # The link issued at release opens the patient view; it names the day of
                # release the German way. The link is exchanged for the httpOnly cookie, which
                # is passed on by hand: a production build marks it Secure, and this smoke
                # speaks plain http to 127.0.0.1.
                link = httpx.URL(r.json()["patient_view_url"])
                with httpx.Client(base_url=WEB, timeout=60.0, follow_redirects=False) as patient:
                    r = patient.get(link.raw_path.decode())
                    assert r.status_code in REDIRECT, ("patient link", r.status_code)
                    issued = re.search(r"hadp_pv=([^;]+)", r.headers.get("set-cookie", ""))
                    assert issued, "patient link issued no hadp_pv cookie"
                    cookie = {"cookie": f"hadp_pv={issued.group(1)}"}
                    page = patient.get("/patient-view", headers=cookie).text
                # React separates adjacent text nodes with empty comments.
                page = page.replace("<!-- -->", "")
                assert re.search(r"Ärztlich freigegeben\s+am \d{2}\.\d{2}\.\d{4}", page), (
                    "patient view does not show the release day as TT.MM.JJJJ"
                )
                checked.append("patient view")
            released = api.get(f"/reports/{report_id}").json()
            assert released["status"] == "released", (
                "release exercise",
                released["status"],
            )
            assert_stage("review page (released)", web.get(review_path).text, released)
            checked.append("released")

            # A value entered now is not one of the six names the import acts on by itself: it
            # waits for review. The table shows it as the source wrote it, with its status —
            # and without a position against its reference interval (65 lies below 70–120).
            r = api.post(
                f"/patients/{pid}/imports",
                json={
                    "values": [
                        {
                            "original_name": "Smoke-Analyt",
                            "original_value": "65",
                            "original_unit": "µg/dL",
                            "reference_low": "70",
                            "reference_high": "120",
                            "observed_at": "2025-06-10T00:00:00Z",
                            "observed_at_is_date_only": True,
                        }
                    ]
                },
            )
            assert r.status_code == 201, ("import", r.status_code, r.text)
            assert r.json()["published_count"] == 0, "a value was published without a human"
            page = web.get(review_path).text.replace("<!-- -->", "")
            row = re.search(
                r"<tr[^>]*>(?:(?!</tr>).)*Smoke-Analyt(?:(?!</tr>).)*</tr>", page, re.DOTALL
            )
            assert row, "the value waiting for review is not in the marker table"
            assert "in Prüfung – nicht veröffentlicht" in row.group(0), "review status not shown"
            assert "Einheit der Quelle" in row.group(0), "the source-unit note is missing"
            assert "Unter Referenz" not in row.group(0), "a position is shown for an unread value"
            checked.append("value in review")

            # A second report, rejected straight from the draft and then reworked: the page
            # must not show a clinical sign-off that never happened, and the reworked
            # version is an edited draft again.
            second = api.post(f"/patients/{pid}/reports").json()
            second_path = f"/patients/{pid}/assessments/{second['report_id']}"
            r = api.post(f"/reports/{second['report_id']}/reject", json={"reason": "wording"})
            assert r.status_code == 200, ("reject", r.status_code, r.text)
            rejected = api.get(f"/reports/{second['report_id']}").json()
            assert rejected["status"] == "rejected", rejected["status"]
            assert_stage("review page (rejected)", web.get(second_path).text, rejected)
            checked.append("rejected")
            statements = [
                {
                    "id": s["id"],
                    "text": s["text"],
                    "evidence_observation_ids": [e["observation_id"] for e in s["evidence"]],
                }
                for s in rejected["statements"]
            ]
            statements[0]["text"] += " (Formulierung geprüft.)"
            r = api.post(f"/reports/{second['report_id']}/edit", json={"statements": statements})
            assert r.status_code == 200, ("edit", r.status_code, r.text)
            reworked = api.get(f"/reports/{second['report_id']}").json()
            assert reworked["status"] == "draft_edited", reworked["status"]
            assert_stage("review page (reworked)", web.get(second_path).text, reworked)
            checked.append("draft_edited")

        r = web.get("/review-queue")
        assert r.status_code == 200, ("/review-queue authed", r.status_code)
        assert "Review-Queue" in r.text, "review queue page did not render"
        assert_no_mock_ui("/review-queue", r.text)

        r = web.get(f"/patients/{pid}/interpretation/neu")
        assert r.status_code == 200, ("/interpretation/neu authed", r.status_code)
        assert "Korrektur-Run erfassen" in r.text or "Interpretation erfassen" in r.text
        assert_no_mock_ui("/interpretation/neu", r.text)

        # The audit trail is tenant administration: this clinician session is told so and
        # is shown no entry.
        r = web.get("/einstellungen/audit")
        assert r.status_code == 200, (
            "/einstellungen/audit as clinician",
            r.status_code,
        )
        assert "nur für Inhaber" in r.text, "audit trail not refused to a non-owner"
        assert "<table" not in r.text, "audit entries rendered for a non-owner"

        # The preparation-time metric is tenant administration as well: no figure, no form.
        r = web.get("/einstellungen/vorbereitungszeit")
        assert r.status_code == 200, (
            "/einstellungen/vorbereitungszeit as clinician",
            r.status_code,
        )
        assert "nur für Inhaber" in r.text, "the metric is not refused to a non-owner"
        # (The shell has a form of its own — the sign-out button.)
        assert "Angaben der Praxis" not in r.text, "the metric is shown to a non-owner"
        assert 'name="median_minutes"' not in r.text, "the metric form is shown to a non-owner"

    # The owner reads the clinic's trail: who did what, on the clinic's wall clock.
    owner = staff_session("owner@demo.synthetic")
    try:
        owner_cookie = {"hadp_session": owner.cookies.get("hadp_session") or ""}
        with httpx.Client(
            base_url=WEB, timeout=60.0, follow_redirects=False, cookies=owner_cookie
        ) as web:

            def entries(path: str) -> str:
                """The table's rows — not the shell around them, which names the reader."""
                r = web.get(path)
                assert r.status_code == 200, (path, r.status_code)
                assert "<tbody" in r.text, f"{path} shows no audit entries"
                return r.text.split("<tbody", 1)[1].split("</tbody>", 1)[0]

            r = web.get("/einstellungen")
            assert 'href="/einstellungen/audit"' in r.text, "settings do not list the audit trail"
            # The preparation-time metric: what the clinic states and what the platform
            # measures stand in two sections, and the page says what the figures are not.
            assert 'href="/einstellungen/vorbereitungszeit"' in r.text, "settings do not list it"
            r = web.get("/einstellungen/vorbereitungszeit")
            assert r.status_code == 200, (
                "/einstellungen/vorbereitungszeit as owner",
                r.status_code,
            )
            assert_no_mock_ui("/einstellungen/vorbereitungszeit", r.text)
            for heading in (
                "Angaben der Praxis",
                "Gemessen aus dem Ablauf der Berichte",
                "Was diese Zahlen sind",
            ):
                assert heading in r.text, f"the metric page lacks the section {heading!r}"
            assert "keine Arbeitszeit" in r.text, "the page does not say what is measured"
            assert 'name="median_minutes"' in r.text, "no form to state a preparation time"
            # An outcome code that is not one of the page's own shows no message.
            r = web.get("/einstellungen/vorbereitungszeit?fehler=nope&gespeichert=yes")
            assert r.status_code == 200, ("metric page with unknown outcome codes", r.status_code)
            assert "nicht gespeichert" not in r.text, "an unknown code shows a failure message"
            assert "wurde gespeichert" not in r.text, "an unknown code shows a success message"
            r = web.get("/einstellungen/audit")
            assert r.status_code == 200, (
                "/einstellungen/audit as owner",
                r.status_code,
            )
            assert_no_mock_ui("/einstellungen/audit", r.text)
            # The page says what the trail does not hold.
            assert "Was dieses Protokoll nicht zeigt" in r.text, "the trail's limits are not stated"
            assert "Derzeit nicht protokolliert" in r.text
            rows = entries("/einstellungen/audit")
            # A colleague's entry into the clinic, named by the account that acted.
            assert "tenant.select" in rows and "Praxis ausgewählt" in rows
            assert "clinician@demo.synthetic" in rows, "audit entries do not name who acted"
            # Every time carries its zone.
            assert re.search(r"\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2}:\d{2} MES?Z", rows), "no zoned time"
            # Reads are part of the trail as it is shown — the reads of the trail included.
            assert "audit.read" in rows, "reading the trail does not show on the trail"
            assert "Audit-Protokoll gelesen" in entries("/einstellungen/audit?category=audit")
            # Reads can be left out, and then the page says that they are.
            r = web.get("/einstellungen/audit?reads=0")
            assert "Lesezugriffe sind ausgeblendet" in r.text
            hidden = entries("/einstellungen/audit?reads=0")
            assert "audit.read" not in hidden and "patient.list" not in hidden
            # A day is a day on the clinic's wall clock: today has this run's entries, and a
            # day that has not come has none.
            today = datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
            assert "tenant.select" in entries(
                f"/einstellungen/audit?from={today}&to={today}&category=tenant"
            )
            r = web.get("/einstellungen/audit?from=2099-01-01")
            assert r.status_code == 200 and "<tbody" not in r.text, "entries from the future"
            assert "keine Einträge" in r.text
            # A parameter that is not what it claims to be is no filter — and is not shown as one.
            r = web.get(
                "/einstellungen/audit?category=nope&target=not-a-uuid&from=yesterday&to=2026-02-30"
            )
            assert r.status_code == 200, (
                "audit trail with malformed filters",
                r.status_code,
            )
            assert "<tbody" in r.text, "a malformed filter emptied the trail"
            # (The address is echoed in the page's own routing data; the form is what counts.)
            assert 'value="2026-02-30"' not in r.text and "Filter zurücksetzen" not in r.text
            r = web.get("/einstellungen/audit?cursor=not-a-cursor")
            assert r.status_code == 200 and "nicht gültig" in r.text, "a damaged position link"
            # One view of the page is one read of the trail, recorded once. (The API read that
            # counts them is not in its own answer.)
            checked_at = datetime.now(UTC).isoformat()
            web.get("/einstellungen/audit")
            reads = owner.get("/audit-events", params={"category": "audit", "since": checked_at})
            assert reads.status_code == 200, reads.text
            assert len(reads.json()["items"]) == 1, "one page view is not one recorded read"
    finally:
        owner.close()

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
