from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from saathi_api.core.errors import Conflict
from tests.conftest import make_token


def _assert_envelope(body: dict[str, object], code: str) -> None:
    err = body["error"]
    assert isinstance(err, dict)
    assert err["code"] == code
    assert isinstance(err["message"], str) and err["message"]
    assert err["requestId"]
    assert isinstance(err["details"], dict)


def test_unknown_route_is_404_envelope(client: TestClient) -> None:
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    _assert_envelope(r.json(), "not_found")


def test_missing_token_is_401(client: TestClient) -> None:
    r = client.get("/api/v1/me")
    assert r.status_code == 401
    _assert_envelope(r.json(), "unauthorized")


def test_bad_tokens_are_401(client: TestClient) -> None:
    for token in ("garbage", make_token(aud="wrong"), make_token(exp=1)):
        r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, token


def test_validation_error_is_400_with_issues(client: TestClient, auth: dict[str, str]) -> None:
    r = client.post("/api/v1/privacy/preview", json={"text": ""}, headers=auth)
    assert r.status_code == 400
    body = r.json()
    _assert_envelope(body, "validation_error")
    assert body["error"]["details"]["issues"][0]["loc"][-1] == "text"


def test_request_id_round_trip(client: TestClient) -> None:
    r = client.get("/health", headers={"X-Request-ID": "req-test-12345"})
    assert r.headers["X-Request-ID"] == "req-test-12345"
    assert r.json()["meta"]["requestId"] == "req-test-12345"
    generated = client.get("/health", headers={"X-Request-ID": "bad id!"}).headers["X-Request-ID"]
    assert generated != "bad id!" and len(generated) == 32


def test_app_error_and_unhandled_error(app: FastAPI) -> None:
    @app.get("/boom-conflict")
    async def conflict() -> None:
        raise Conflict("already done", details={"status": "executed"})

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internals")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/boom-conflict")
        assert r.status_code == 409
        _assert_envelope(r.json(), "conflict")
        assert r.json()["error"]["details"] == {"status": "executed"}

        r = c.get("/boom")
        assert r.status_code == 500
        _assert_envelope(r.json(), "internal_error")
        assert "secret internals" not in r.text
        assert r.headers["X-Request-ID"] == r.json()["error"]["requestId"]


def test_success_envelope_shape(
    client: TestClient, auth: dict[str, str], user_id: uuid.UUID
) -> None:
    r = client.get("/api/v1/me", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["id"] == str(user_id)
    assert body["data"]["isDemo"] is True and body["data"]["locale"] == "hi-IN"
    assert set(body["meta"]) == {"requestId", "nextCursor"}


def test_rate_limit_returns_429_with_retry_after(client: TestClient, auth: dict[str, str]) -> None:
    client.app.state.services.settings.rate_limit_default_per_min = 2  # type: ignore[attr-defined]
    codes = [client.get("/api/v1/me", headers=auth).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    r = client.get("/api/v1/me", headers=auth)
    assert r.json()["error"]["code"] == "rate_limited"
    assert int(r.headers["Retry-After"]) >= 1
