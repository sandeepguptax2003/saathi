from __future__ import annotations

import uuid

from saathi_api.core.pagination import PageParams, encode_cursor
from saathi_api.modules.privacy.masker import MaskSession
from saathi_api.modules.privacy.models import PrivacyEvent
from saathi_api.modules.privacy.repository import PrivacyRepository
from saathi_api.modules.privacy.schemas import PrivacyEventOut, PrivacyPreviewIn, PrivacyPreviewOut


class PrivacyService:
    def __init__(self, repo: PrivacyRepository) -> None:
        self.repo = repo

    @staticmethod
    def preview(body: PrivacyPreviewIn) -> PrivacyPreviewOut:
        result = MaskSession(known_names=tuple(body.known_names)).mask(body.text)
        return PrivacyPreviewOut(
            masked_text=result.masked_text,
            entity_counts=result.entity_counts,
            total_masked=sum(result.entity_counts.values()),
        )

    async def record(
        self, user_id: uuid.UUID, entity_counts: dict[str, int], message_id: uuid.UUID | None
    ) -> None:
        await self.repo.add(
            PrivacyEvent(user_id=user_id, message_id=message_id, entity_counts=dict(entity_counts))
        )

    async def list_events(
        self, user_id: uuid.UUID, page: PageParams
    ) -> tuple[list[PrivacyEventOut], str | None]:
        rows = await self.repo.list_page(user_id, page)
        next_cursor = None
        if len(rows) > page.limit:
            rows = rows[: page.limit]
            next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id)
        return [PrivacyEventOut.model_validate(r) for r in rows], next_cursor
