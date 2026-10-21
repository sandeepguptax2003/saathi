from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import available_timezones

from pydantic import Field, field_validator

from saathi_api.core.schemas import CamelModel

Locale = Literal["hi-IN", "en-IN"]


class MeOut(CamelModel):
    id: uuid.UUID
    display_name: str | None
    locale: Locale
    timezone: str
    voice_pref: str | None
    daily_budget_usd: float | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class MePatch(CamelModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    locale: Locale | None = None
    timezone: str | None = None
    voice_pref: str | None = Field(default=None, max_length=64)
    daily_budget_usd: float | None = Field(default=None, gt=0, le=100)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        if v is not None and v not in available_timezones():
            raise ValueError("unknown IANA timezone")
        return v
