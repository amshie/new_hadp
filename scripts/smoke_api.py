"""Live smoke test against a running API (uvicorn).

Walks the full vertical-spike happy path over real HTTP against seeded synthetic data:
login -> select tenant -> list patients -> timeline -> draft -> approve -> release ->
patient view, plus a negative check that a bad token reveals nothing. Exits non-zero on
any failure. Synthetic data only.
"""

from __future__ import annotations

import sys

import httpx

BASE = "http://127.0.0.1:8000/api/v1"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=10.0) as c:
        health = c.get("/health").json()
        assert health["status"] == "ok", health

        assert c.post("/auth/dev-login", json={"email": "clinician@demo.synthetic"}).status_code == 200

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

        # safety: cannot release before approval
        assert c.post(f"/reports/{report_id}/release").status_code == 409

        assert c.post(f"/reports/{report_id}/approve").json()["status"] == "approved"
        release = c.post(f"/reports/{report_id}/release").json()
        token = release["patient_access_token"]

    # patient view: separate client (no staff cookie)
    with httpx.Client(base_url=BASE, timeout=10.0) as anon:
        view = anon.get("/patient-view", params={"tenant": tenant["tenant_id"], "token": token})
        assert view.status_code == 200, view.text
        assert view.json()["status"] == "released"
        bad = anon.get("/patient-view", params={"tenant": tenant["tenant_id"], "token": "nope"})
        assert bad.status_code == 404, bad.text

    print("SMOKE OK: full happy path passed over live HTTP")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - smoke script: report and fail
        print(f"SMOKE FAILED: {exc!r}")
        sys.exit(1)
