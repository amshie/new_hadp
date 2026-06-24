from __future__ import annotations


def test_health_ok(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app_env"] == "test"
    assert body["synthetic_data_only"] is True


def test_security_headers_present(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/health")
    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "x-correlation-id" in resp.headers
