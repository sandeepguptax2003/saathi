from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.fakes import FakeDB


def test_health_ok_and_security_headers(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "ok" and data["db"] == "ok" and data["env"] == "test"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in r.headers  # only in production


def test_health_stays_200_when_db_down_but_ready_is_503(app: FastAPI) -> None:
    app.state.services.db = FakeDB(healthy=False)
    with TestClient(app) as c:
        h = c.get("/health")
        assert h.status_code == 200 and h.json()["data"]["db"] == "down"
        r = c.get("/ready")
        assert r.status_code == 503
        assert r.json()["data"] == {"status": "not_ready", "checks": {"db": "down", "llm": "ok"}}


def test_ready_ok(client: TestClient) -> None:
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ready"


def test_versioned_health_alias(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 200


def test_cors_allowlist(client: TestClient) -> None:
    ok = client.options(
        "/api/v1/me",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options(
        "/api/v1/me",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers
