"""privacy_events: per-message entity counts. Never stores raw PII."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from saathi_api.core.db import Base, IdMixin, TimestampMixin


class PrivacyEvent(IdMixin, TimestampMixin, Base):
    __tablename__ = "privacy_events"
    __table_args__ = (Index("ix_privacy_events_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    entity_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
