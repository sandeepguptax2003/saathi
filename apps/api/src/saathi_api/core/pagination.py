"""Opaque base64 cursor pagination: cursor = base64url("<iso-timestamp>|<uuid>")."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Query

from saathi_api.core.errors import ValidationFailed

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(frozen=True, slots=True)
class Cursor:
    ts: datetime
    id: UUID


def encode_cursor(ts: datetime, id_: UUID) -> str:
    raw = f"{ts.isoformat()}|{id_}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str) -> Cursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        ts_s, id_s = base64.urlsafe_b64decode(padded.encode()).decode().split("|", 1)
        ts = datetime.fromisoformat(ts_s)
        if ts.tzinfo is None:
            raise ValueError("naive")
        return Cursor(ts=ts, id=UUID(id_s))
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationFailed("Invalid cursor", details={"field": "cursor"}) from exc


@dataclass(frozen=True, slots=True)
class PageParams:
    cursor: Cursor | None
    limit: int


def page_params(
    cursor: Annotated[str | None, Query(max_length=256)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> PageParams:
    return PageParams(cursor=decode_cursor(cursor) if cursor else None, limit=limit)
