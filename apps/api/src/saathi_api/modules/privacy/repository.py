from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.core.pagination import PageParams
from saathi_api.modules.privacy.models import PrivacyEvent


class PrivacyRepository(Protocol):
    async def add(self, event: PrivacyEvent) -> PrivacyEvent: ...
    async def list_page(self, user_id: uuid.UUID, page: PageParams) -> list[PrivacyEvent]: ...
    async def commit(self) -> None: ...


class SqlPrivacyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: PrivacyEvent) -> PrivacyEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_page(self, user_id: uuid.UUID, page: PageParams) -> list[PrivacyEvent]:
        stmt = select(PrivacyEvent).where(PrivacyEvent.user_id == user_id)
        if page.cursor:
            c = page.cursor
            stmt = stmt.where(
                or_(
                    PrivacyEvent.created_at < c.ts,
                    and_(PrivacyEvent.created_at == c.ts, PrivacyEvent.id < c.id),
                )
            )
        stmt = stmt.order_by(PrivacyEvent.created_at.desc(), PrivacyEvent.id.desc()).limit(
            page.limit + 1
        )
        return list((await self.session.scalars(stmt)).all())

    async def commit(self) -> None:
        await self.session.commit()
