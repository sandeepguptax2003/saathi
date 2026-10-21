from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from saathi_api.core.schemas import CamelModel


class PrivacyPreviewIn(CamelModel):
    text: str = Field(min_length=1, max_length=4000)
    known_names: list[str] = Field(default_factory=list, max_length=50)


class PrivacyPreviewOut(CamelModel):
    masked_text: str
    entity_counts: dict[str, int]
    total_masked: int


class PrivacyEventOut(CamelModel):
    id: uuid.UUID
    message_id: uuid.UUID | None
    entity_counts: dict[str, int]
    created_at: datetime
