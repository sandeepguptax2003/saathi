from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.core.pagination import PageParams
from saathi_api.modules.approvals.models import AuditLog, PendingAction


class ApprovalsRepository(Protocol):
    async def add(self, action: PendingAction) -> PendingAction: ...
    async def get_for_update(
        self, user_id: uuid.UUID, action_id: uuid.UUID
    ) -> PendingAction | None: ...
    async def get_by_idempotency_key(self, key: str) -> PendingAction | None: ...
    async def list_page(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> list[PendingAction]: ...
    async def expire_stale(self, user_id: uuid.UUID, now: datetime) -> int: ...
    async def delete_for_user(self, user_id: uuid.UUID) -> int: ...
    async def audit(self, entry: AuditLog) -> None: ...
    async def commit(self) -> None: ...


class SqlApprovalsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, action: PendingAction) -> PendingAction:
        self.session.add(action)
        await self.session.flush()
        return action

    async def get_for_update(
        self, user_id: uuid.UUID, action_id: uuid.UUID
    ) -> PendingAction | None:
        stmt = (
            select(PendingAction)
            .where(PendingAction.id == action_id, PendingAction.user_id == user_id)
            .with_for_update()
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_idempotency_key(self, key: str) -> PendingAction | None:
        stmt = select(PendingAction).where(PendingAction.idempotency_key == key)
        return (await self.session.scalars(stmt)).first()

    async def list_page(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> list[PendingAction]:
        stmt = select(PendingAction).where(PendingAction.user_id == user_id)
        if status:
            stmt = stmt.where(PendingAction.status == status)
        if page.cursor:
            c = page.cursor
            stmt = stmt.where(
                or_(
                    PendingAction.created_at < c.ts,
                    and_(PendingAction.created_at == c.ts, PendingAction.id < c.id),
                )
            )
        stmt = stmt.order_by(PendingAction.created_at.desc(), PendingAction.id.desc()).limit(
            page.limit + 1
        )
        return list((await self.session.scalars(stmt)).all())

    async def expire_stale(self, user_id: uuid.UUID, now: datetime) -> int:
        result = await self.session.execute(
            update(PendingAction)
            .where(
                PendingAction.user_id == user_id,
                PendingAction.status == "pending",
                PendingAction.expires_at < now,
            )
            .values(status="expired")
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(PendingAction).where(PendingAction.user_id == user_id)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def audit(self, entry: AuditLog) -> None:
        self.session.add(entry)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
