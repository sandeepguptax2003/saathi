from __future__ import annotations

import time
import uuid
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from saathi_api.core import security
from saathi_api.core.errors import Unauthorized
from tests.conftest import make_settings


def _claims(sub: uuid.UUID) -> dict[str, Any]:
    now = int(time.time())
    return {
        "sub": str(sub),
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 300,
    }


def test_hs256_token_verified_with_project_secret() -> None:
    settings = make_settings()
    uid = uuid.uuid4()
    token = jwt.encode(
        _claims(uid), settings.supabase_jwt_secret.get_secret_value(), algorithm="HS256"
    )
    assert security.decode_supabase_jwt(token, settings).id == uid


def test_es256_token_verified_via_jwks(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings()
    private_key = ec.generate_private_key(ec.SECP256R1())

    class FakeSigningKey:
        key = private_key.public_key()

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            return FakeSigningKey()

    monkeypatch.setattr(security, "_jwks_client", lambda _s: FakeJWKClient())
    uid = uuid.uuid4()
    token = jwt.encode(_claims(uid), private_key, algorithm="ES256", headers={"kid": "k1"})
    assert security.decode_supabase_jwt(token, settings).id == uid


def test_es256_token_with_wrong_key_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings()
    signer = ec.generate_private_key(ec.SECP256R1())
    other = ec.generate_private_key(ec.SECP256R1())

    class FakeSigningKey:
        key = other.public_key()

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            return FakeSigningKey()

    monkeypatch.setattr(security, "_jwks_client", lambda _s: FakeJWKClient())
    token = jwt.encode(_claims(uuid.uuid4()), signer, algorithm="ES256")
    with pytest.raises(Unauthorized):
        security.decode_supabase_jwt(token, settings)


def test_unsupported_alg_rejected() -> None:
    token = jwt.encode(_claims(uuid.uuid4()), "x" * 48, algorithm="HS512")
    with pytest.raises(Unauthorized):
        security.decode_supabase_jwt(token, make_settings())


def test_jwks_url_is_supabase_auth_endpoint() -> None:
    s = make_settings(supabase_url="https://ref.supabase.co/")
    assert security.jwks_url(s) == "https://ref.supabase.co/auth/v1/.well-known/jwks.json"
