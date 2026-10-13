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

With WEB_SMOKE_FORWARDED=1 (CI, where the API is started with TRUSTED_PROXIES naming the web
server) one patient-view request is sent the way a proxy in front of the web server would
pass it on, and the limiter's own counter is read: the web server handed the client's
address to the API, and the API counted that address — not the web server's.
"""

from __future__ import annotations

import os
import re
import sys
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
import redis

WEB = os.environ.get("WEB_SMOKE_BASE", "http://127.0.0.1:3000")
API = os.environ.get("API_SMOKE_BASE", "http://127.0.0.1:8000/api/v1")
REDIRECT = {301, 302, 303, 307, 308}
EXERCISE_RELEASE = os.environ.get("WEB_SMOKE_RELEASE") == "1"
CHECK_FORWARDING = os.environ.get("WEB_SMOKE_FORWARDED") == "1"

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


def shown(response: httpx.Response) -> str:
    """A page's markup without its scripts — what it shows, not everything it carries.

    The wording of the chosen interface language travels to the browser inside a script of
    every page (apps/web/src/lib/i18n: the root layout hands it to the provider), and so does
    the data of every client component. A word of the dictionary is therefore in the raw
    HTML of every page whether the page shows it or not: read raw, "this page says X" cannot
    fail and "this page does not say X" fails for a page that does not say it.
    """
    return re.sub(r"<script\b[^>]*>.*?</script>", "", response.text, flags=re.S)


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


def assert_client_address_is_passed_on() -> None:
    """Browser -> web server -> API: the limit on the patient view counts the client.

    Addresses of the documentation ranges (RFC 5737). The clinic named does not exist, so the
    request is refused and nothing reaches a trail; the counters it leaves expire in a minute.
    """
    from hadp_api.config import get_settings  # the Redis the API under test uses

    seen_by_proxy = "203.0.113.77"  # what a proxy in front of the web server adds
    written_by_client = "198.51.100.77"  # what the client put into the header itself
    stepped_over = "203.0.113.78"  # see the second request
    store = redis.Redis.from_url(get_settings().redis_url, socket_timeout=5)
    counters = [f"rl:patient_view:{address}" for address in (seen_by_proxy, written_by_client)]
    store.delete(*counters, f"rl:patient_view:{stepped_over}")

    def refused_view(forwarded: str) -> None:
        with httpx.Client(base_url=WEB, timeout=60.0, follow_redirects=False) as patient:
            r = patient.get(
                "/patient-view",
                headers={
                    "cookie": f"hadp_pv={uuid.uuid4()}:synthetic-smoke",
                    "x-forwarded-for": forwarded,
                },
            )
        assert r.status_code == 200, ("/patient-view with a forwarded address", r.status_code)
        assert "Dieser Bericht ist nicht verfügbar." in shown(r), "the wrong link was not refused"

    refused_view(f"{written_by_client}, {seen_by_proxy}")
    counted = [store.get(counter) for counter in counters]
    assert counted == [b"1", None], (
        "the patient view was not counted under the address the proxy named "
        "(is the API started with TRUSTED_PROXIES naming the web server?)",
        counted,
    )
    # One reader of the header. The right-most entry is now this machine's own address: the
    # API reads the entry it was told to and counts that. uvicorn's own handling of the header
    # — on unless the API server is started with --no-proxy-headers — would step over an
    # address it trusts and hand the API the one before it as the peer.
    refused_view(f"{stepped_over}, 127.0.0.1")
    assert store.get(f"rl:patient_view:{stepped_over}") is None, (
        "the entry before the web server's own address was counted: "
        "is the API server started without --no-proxy-headers?"
    )


def assert_interface_language() -> None:
    """German without a choice, English for a device that chose it (apps/web/src/lib/i18n).

    The choice is a cookie; a value that names no offered language counts as no choice.
    """

    def page(path: str, choice: str | None) -> httpx.Response:
        headers = {"cookie": f"hadp_locale={choice}"} if choice else {}
        with httpx.Client(base_url=WEB, timeout=60.0, follow_redirects=False) as device:
            return device.get(path, headers=headers)

    r = page("/login", "en")
    assert '<html lang="en"' in shown(r), "/login does not name English as its language"
    assert "Clinical access" in shown(r) and "Klinischer Zugang" not in shown(r), (
        "/login in English"
    )
    r = page("/this-route-does-not-exist", "en")
    assert r.status_code == 404 and "Page not found" in shown(r), "the not-found page in English"
    for choice in (None, "fr", "EN"):
        r = page("/login", choice)
        assert '<html lang="de"' in shown(r) and "Klinischer Zugang" in shown(r), (
            "/login is not German for a device without a valid choice",
            choice,
        )


def main() -> int:
    assert_interface_language()
    # Unauthenticated: deny-by-default guards + retired-route redirect + 404 boundary.
    with httpx.Client(base_url=WEB, timeout=60.0, follow_redirects=False) as web:
        r = web.get("/login")
        assert r.status_code == 200, ("/login", r.status_code)
        assert "Klinischer Zugang" in shown(r), "/login did not render the sign-in card"
        # The development sign-in asks for an account's e-mail address and nothing else.
        assert 'name="email"' in shown(r), "/login offers no sign-in form in dev mode"
        assert "Zwei-Faktor" not in shown(r), "/login still shows a second-factor step"
        assert_no_mock_ui("/login", shown(r))

        for path in ("/", "/overview", "/review-queue"):
            r = web.get(path)
            assert r.status_code in REDIRECT, (path, r.status_code)
            assert "/login" in r.headers["location"], (path, r.headers["location"])

        r = web.get("/worklist")
        assert r.status_code in REDIRECT, ("/worklist", r.status_code)
        assert "/overview" in r.headers["location"], r.headers["location"]

        r = web.get("/this-route-does-not-exist")
        assert r.status_code == 404, ("unknown route", r.status_code)
        assert "Seite nicht gefunden" in shown(r), "not-found boundary did not render"

        # Patient-facing pages: neutral fail states + the four-part disclaimer, no fetch
        # on a malformed link (UUID guard), German copy.
        r = web.get("/einladung?tenant=not-a-uuid&token=x")
        assert r.status_code == 200, ("/einladung guard", r.status_code)
        assert "nicht oder nicht mehr gültig" in shown(r)
        assert "Pilotumgebung" in shown(r), "disclaimer missing on /einladung"

        r = web.get("/patient-view")
        assert r.status_code == 200, ("/patient-view neutral", r.status_code)
        assert "nicht oder nicht mehr gültig" in shown(r)
        assert "Pilotumgebung" in shown(r), "disclaimer missing on /patient-view"

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
        assert "Synthetische Beispieldaten" in shown(r), "synthetic banner missing on /overview"
        assert_no_mock_ui("/overview", shown(r))
        # Every navigation entry leads somewhere: the four real destinations, nothing else.
        assert_nav("/overview", shown(r), "vb-nav")

        r = web.get("/patients")
        assert r.status_code == 200, ("/patients authed", r.status_code)
        assert_no_mock_ui("/patients", shown(r))

        # The pages translated so far, in the language of the device: German without a choice,
        # English by choice — each with the wording of its own language and none of the other.
        # The overview names all five places a report can stand in, whatever the data.
        wording = {
            "/overview": {
                "de": ("Klinische Arbeitsliste", "In Prüfung", "Kein Entwurf"),
                "en": ("Clinical work list", "In review", "No draft"),
            },
            "/patients": {
                "de": ("Patientenverzeichnis", "Ohne Bericht"),
                "en": ("Patient directory", "No report"),
            },
        }
        for path, words in wording.items():
            for language, other in (("de", "en"), ("en", "de")):
                cookie = f"hadp_session={session}"
                if language == "en":
                    cookie += "; hadp_locale=en"
                page = shown(web.get(path, headers={"cookie": cookie}))
                for word in words[language]:
                    assert word in page, f"{path} ({language}) does not say {word!r}"
                for word in words[other]:
                    assert word not in page, f"{path} ({language}) says {word!r}"

        r = web.get(f"/patients/{pid}")
        assert r.status_code == 200, ("/patients/[id] authed", r.status_code)
        assert_no_mock_ui("/patients/[id]", shown(r))
        # The seeded patient has a report: the detail page must link to its review surface
        # (the only place approve/release live), and that link must resolve.
        review = re.search(rf'href="(/patients/{pid}/assessments/[0-9a-f-]{{36}})"', shown(r))
        assert review, "patient detail does not link to the report review page"
        # Laboratory file intake lives on the patient page (care staff): the card and its
        # file field must render.
        assert "Labordaten" in shown(r), "patient detail has no laboratory-files card"
        assert 'type="file"' in shown(r), "laboratory-files card has no upload field"
        # Consent state per purpose is shown on the patient page (all staff).
        assert "Einwilligungen" in shown(r), "patient detail has no consent card"
        assert "Freigabe geprüfter Berichte" in shown(r), "consent card lists no purposes"
        # The data export is tenant administration (owner): this clinician session sees no card.
        assert "Datenauskunft erstellen" not in shown(r), "data-export card shown to a non-owner"
        review_path = review.group(1)
        report_id = review_path.rsplit("/", 1)[1]
        r = web.get(review_path)
        assert r.status_code == 200, ("review page via detail link", r.status_code)
        assert f'href="/patients/{pid}"' in shown(r), "review page has no way back to the patient"
        assert_no_mock_ui("review page", shown(r))
        # The legacy shell's navigation leads to the real pages (it used to be dead links).
        assert_nav("review page", shown(r), "nav-link")
        report = api.get(f"/reports/{report_id}").json()
        assert_stage("review page", shown(r), report)
        checked = [report["status"]]

        if EXERCISE_RELEASE:
            # Two-tier gate through the API (clinician approves, medical director releases),
            # then the same page must say "freigegeben" — and nowhere "nicht freigegeben".
            if report["status"] in ("draft_generated", "draft_edited"):
                r = api.post(f"/reports/{report_id}/approve")
                assert r.status_code == 200, ("approve", r.status_code, r.text)
                page = shown(web.get(review_path))
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
                    page = shown(patient.get("/patient-view", headers=cookie))
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
            assert_stage("review page (released)", shown(web.get(review_path)), released)
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
            page = shown(web.get(review_path)).replace("<!-- -->", "")
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
            assert_stage("review page (rejected)", shown(web.get(second_path)), rejected)
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
            assert_stage("review page (reworked)", shown(web.get(second_path)), reworked)
            checked.append("draft_edited")

        r = web.get("/review-queue")
        assert r.status_code == 200, ("/review-queue authed", r.status_code)
        assert "Review-Queue" in shown(r), "review queue page did not render"
        assert_no_mock_ui("/review-queue", shown(r))

        r = web.get(f"/patients/{pid}/interpretation/neu")
        assert r.status_code == 200, ("/interpretation/neu authed", r.status_code)
        assert "Korrektur-Run erfassen" in shown(r) or "Interpretation erfassen" in shown(r)
        assert_no_mock_ui("/interpretation/neu", shown(r))

        # The audit trail is tenant administration: this clinician session is told so and
        # is shown no entry.
        r = web.get("/einstellungen/audit")
        assert r.status_code == 200, (
            "/einstellungen/audit as clinician",
            r.status_code,
        )
        assert "nur für Inhaber" in shown(r), "audit trail not refused to a non-owner"
        assert "<table" not in shown(r), "audit entries rendered for a non-owner"

        # The preparation-time metric is tenant administration as well: no figure, no form.
        r = web.get("/einstellungen/vorbereitungszeit")
        assert r.status_code == 200, (
            "/einstellungen/vorbereitungszeit as clinician",
            r.status_code,
        )
        assert "nur für Inhaber" in shown(r), "the metric is not refused to a non-owner"
        # (The shell has a form of its own — the sign-out button.)
        assert "Angaben der Praxis" not in shown(r), "the metric is shown to a non-owner"
        assert 'name="median_minutes"' not in shown(r), "the metric form is shown to a non-owner"

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
                assert "<tbody" in shown(r), f"{path} shows no audit entries"
                return shown(r).split("<tbody", 1)[1].split("</tbody>", 1)[0]

            r = web.get("/einstellungen")
            assert 'href="/einstellungen/audit"' in shown(r), "settings do not list the audit trail"
            # The preparation-time metric: what the clinic states and what the platform
            # measures stand in two sections, and the page says what the figures are not.
            assert 'href="/einstellungen/vorbereitungszeit"' in shown(r), "settings do not list it"
            r = web.get("/einstellungen/vorbereitungszeit")
            assert r.status_code == 200, (
                "/einstellungen/vorbereitungszeit as owner",
                r.status_code,
            )
            assert_no_mock_ui("/einstellungen/vorbereitungszeit", shown(r))
            for heading in (
                "Angaben der Praxis",
                "Gemessen aus dem Ablauf der Berichte",
                "Was diese Zahlen sind",
            ):
                assert heading in shown(r), f"the metric page lacks the section {heading!r}"
            assert "keine Arbeitszeit" in shown(r), "the page does not say what is measured"
            assert 'name="median_minutes"' in shown(r), "no form to state a preparation time"
            # An outcome code that is not one of the page's own shows no message.
            r = web.get("/einstellungen/vorbereitungszeit?fehler=nope&gespeichert=yes")
            assert r.status_code == 200, ("metric page with unknown outcome codes", r.status_code)
            assert "nicht gespeichert" not in shown(r), "an unknown code shows a failure message"
            assert "wurde gespeichert" not in shown(r), "an unknown code shows a success message"
            r = web.get("/einstellungen/audit")
            assert r.status_code == 200, (
                "/einstellungen/audit as owner",
                r.status_code,
            )
            assert_no_mock_ui("/einstellungen/audit", shown(r))
            # The page says what the trail does not hold.
            assert "Was dieses Protokoll nicht zeigt" in shown(r), (
                "the trail's limits are not stated"
            )
            assert "Derzeit nicht protokolliert" in shown(r)
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
            assert "Lesezugriffe sind ausgeblendet" in shown(r)
            hidden = entries("/einstellungen/audit?reads=0")
            assert "audit.read" not in hidden and "patient.list" not in hidden
            # A day is a day on the clinic's wall clock: today has this run's entries, and a
            # day that has not come has none.
            today = datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
            assert "tenant.select" in entries(
                f"/einstellungen/audit?from={today}&to={today}&category=tenant"
            )
            r = web.get("/einstellungen/audit?from=2099-01-01")
            assert r.status_code == 200 and "<tbody" not in shown(r), "entries from the future"
            assert "keine Einträge" in shown(r)
            # A parameter that is not what it claims to be is no filter — and is not shown as one.
            r = web.get(
                "/einstellungen/audit?category=nope&target=not-a-uuid&from=yesterday&to=2026-02-30"
            )
            assert r.status_code == 200, (
                "audit trail with malformed filters",
                r.status_code,
            )
            assert "<tbody" in shown(r), "a malformed filter emptied the trail"
            # (The address is echoed in the page's own routing data; the form is what counts.)
            assert 'value="2026-02-30"' not in shown(r) and "Filter zurücksetzen" not in shown(r)
            r = web.get("/einstellungen/audit?cursor=not-a-cursor")
            assert r.status_code == 200 and "nicht gültig" in shown(r), "a damaged position link"
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
    if CHECK_FORWARDING:
        assert_client_address_is_passed_on()
    print("WEB SMOKE OK: guards, redirects, 404 boundary, and authed dashboard render")
    print(f"  report status wording checked for: {', '.join(checked)}")
    forwarding = "checked" if CHECK_FORWARDING else "not checked (WEB_SMOKE_FORWARDED is unset)"
    print(f"  client address passed on to the API: {forwarding}")
    print(
        "  interface language: German by default, English by choice, on /login, the 404 page,"
        " /overview and /patients"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - smoke script: report and fail
        print(f"WEB SMOKE FAILED: {exc!r}")
        sys.exit(1)
