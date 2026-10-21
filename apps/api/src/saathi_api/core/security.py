"""Supabase JWT verification (HS256 project secret) and the current-user dependency."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


def decode_supabase_jwt(token: str, settings: Settings) -> AuthUser:
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            settings.supabase_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
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
    user = decode_supabase_jwt(creds.credentials, _settings_from(request))
    user_id_var.set(str(user.id))
    structlog.contextvars.bind_contextvars(user=user.log_hash)
    return user


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
