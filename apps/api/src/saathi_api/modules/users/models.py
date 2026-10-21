from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from saathi_api.core.db import Base, TimestampMixin


class User(TimestampMixin, Base):
    """One row per Supabase auth user; id == auth.users.id (set explicitly, no default)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="hi-IN")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    voice_pref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    daily_budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
