"""Live smoke test against a running API (uvicorn).

Walks the full vertical-spike happy path over real HTTP against seeded synthetic data:
clinician login -> select tenant -> list patients -> timeline -> draft -> approve, then
the TWO-TIER physician gate: the clinician may NOT release (403); the medical director
releases -> patient view, plus a negative check that a bad token reveals nothing.
Exits non-zero on any failure. Synthetic data only.
"""

from __future__ import annotations

import os
import sys

import httpx

# The same override the web smoke has, so both can run against another local instance.
BASE = os.environ.get("API_SMOKE_BASE", "http://127.0.0.1:8000/api/v1")


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=10.0) as c:
        health = c.get("/health").json()
        assert health["status"] == "ok", health

        assert c.post("/auth/dev-login", json={"email": "clinician@demo.synthetic"}).status_code == 200
        c.headers["x-csrf-token"] = c.cookies.get("hadp_csrf") or ""

        tenants = c.get("/tenancy/my-tenants").json()
        tenant = next(t for t in tenants if t["tenant_slug"] == "demo-clinic")
        assert c.post("/tenancy/select-tenant", json={"tenant_id": tenant["tenant_id"]}).status_code == 200

        patients = c.get("/patients").json()
        patient = next(p for p in patients if p["external_ref"] == "SYN-0001")
        pid = patient["id"]

        timeline = c.get(f"/patients/{pid}/observations").json()
        assert len(timeline) >= 2, timeline
        # The two LDL observations yield a deterministic delta; assert by metric, not by position
        # (same-date marker observations also seed the timeline, so the LDL row is not last).
        ldl = [p for p in timeline if p["metric_code"] == "13457-7"]
        assert any(p["delta_vs_previous"] == "-0.8" for p in ldl), ldl

        draft = c.post(f"/patients/{pid}/reports").json()
        report_id = draft["report_id"]
        assert draft["status"] == "draft_generated"
        assert all(len(s["evidence"]) >= 1 for s in draft["statements"]), draft

        assert c.post(f"/reports/{report_id}/approve").json()["status"] == "approved"
        # Two-tier physician gate: the clinician approves but may NOT release.
        assert c.post(f"/reports/{report_id}/release").status_code == 403

    # Release is the medical director's lock (separate session).
    with httpx.Client(base_url=BASE, timeout=10.0) as md:
        assert (
            md.post(
                "/auth/dev-login", json={"email": "medical.director@demo.synthetic"}
            ).status_code
            == 200
        )
        md.headers["x-csrf-token"] = md.cookies.get("hadp_csrf") or ""
        md_tenant = next(
            t for t in md.get("/tenancy/my-tenants").json() if t["tenant_slug"] == "demo-clinic"
        )
        assert (
            md.post("/tenancy/select-tenant", json={"tenant_id": md_tenant["tenant_id"]}).status_code
            == 200
        )
        release = md.post(f"/reports/{report_id}/release").json()
        token = release["patient_access_token"]

    # patient view: separate client (no staff cookie). Token travels in the POST body,
    # never the URL — so it stays out of query strings, history, and access logs.
    with httpx.Client(base_url=BASE, timeout=10.0) as anon:
        view = anon.post(
            "/patient-view", json={"tenant": tenant["tenant_id"], "token": token}
        )
        assert view.status_code == 200, view.text
        assert view.json()["status"] == "released"
        bad = anon.post(
            "/patient-view", json={"tenant": tenant["tenant_id"], "token": "nope"}
        )
        assert bad.status_code == 404, bad.text

    print("SMOKE OK: full happy path passed over live HTTP")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - smoke script: report and fail
        print(f"SMOKE FAILED: {exc!r}")
        sys.exit(1)
