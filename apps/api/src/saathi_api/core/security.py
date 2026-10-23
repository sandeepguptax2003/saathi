"""Supabase JWT verification and the current-user dependency.

Supabase projects sign access tokens either with the legacy HS256 project secret or,
on newer projects, with asymmetric keys (ES256/RS256) published at the project's JWKS
endpoint. Both are accepted: the token header's ``alg`` picks the verifier.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from saathi_api.core.config import Settings
from saathi_api.core.context import user_id_var
from saathi_api.core.errors import Unauthorized

_bearer = HTTPBearer(auto_error=False, description="Supabase access token")


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: uuid.UUID
    is_anonymous: bool
    email: str | None
    role: str

    @property
    def log_hash(self) -> str:
        return hashlib.sha256(self.id.bytes).hexdigest()[:12]


_ASYMMETRIC_ALGS = frozenset({"ES256", "RS256", "EdDSA"})
_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def jwks_url(settings: Settings) -> str:
    return settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"


def _jwks_client(settings: Settings) -> jwt.PyJWKClient:
    url = jwks_url(settings)
    client = _jwks_clients.get(url)
    if client is None:
        client = jwt.PyJWKClient(url, cache_keys=True, lifespan=600, timeout=5)
        _jwks_clients[url] = client
    return client


def _verification_key(token: str, settings: Settings) -> tuple[Any, list[str]]:
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        return settings.supabase_jwt_secret.get_secret_value(), ["HS256"]
    if alg in _ASYMMETRIC_ALGS:
        return _jwks_client(settings).get_signing_key_from_jwt(token).key, [str(alg)]
    raise jwt.InvalidAlgorithmError(f"Unsupported alg {alg!r}")


def decode_supabase_jwt(token: str, settings: Settings) -> AuthUser:
    try:
        key, algorithms = _verification_key(token, settings)
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=settings.supabase_jwt_audience,
            options={"require": ["exp", "sub"]},
            leeway=10,
        )
        user_id = uuid.UUID(str(claims["sub"]))
    except (jwt.PyJWTError, ValueError) as exc:
        raise Unauthorized("Invalid or expired token") from exc
    role = str(claims.get("role", "authenticated"))
    if role not in {"authenticated", "anon"}:
        raise Unauthorized("Unsupported token role")
    return AuthUser(
        id=user_id,
        is_anonymous=bool(claims.get("is_anonymous", False)),
        email=claims.get("email") or None,
        role=role,
    )


def _settings_from(request: Request) -> Settings:
    settings: Settings = request.app.state.services.settings
    return settings


async def get_current_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthUser:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise Unauthorized("Authorization: Bearer <token> required")
    # JWKS lookups can hit the network on a cache miss, so keep them off the event loop.
    user = await run_in_threadpool(decode_supabase_jwt, creds.credentials, _settings_from(request))
    user_id_var.set(str(user.id))
    structlog.contextvars.bind_contextvars(user=user.log_hash)
    return user


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
