from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.core.pagination import PageParams
from saathi_api.modules.skills.models import Reminder, SkillRun


class SkillsRepository(Protocol):
    async def add_reminder(self, reminder: Reminder) -> Reminder: ...
    async def get_reminder(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder | None: ...
    async def list_reminders(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> list[Reminder]: ...
    async def delete_reminder(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> bool: ...
    async def delete_reminders_for_user(self, user_id: uuid.UUID) -> int: ...
    async def add_run(self, run: SkillRun) -> None: ...
    async def commit(self) -> None: ...


class SqlSkillsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_reminder(self, reminder: Reminder) -> Reminder:
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get_reminder(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder | None:
        stmt = select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
        return (await self.session.scalars(stmt)).first()

    async def list_reminders(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> list[Reminder]:
        stmt = select(Reminder).where(Reminder.user_id == user_id)
        if status:
            stmt = stmt.where(Reminder.status == status)
        if page.cursor:
            c = page.cursor
            stmt = stmt.where(
                or_(Reminder.due_at > c.ts, and_(Reminder.due_at == c.ts, Reminder.id > c.id))
            )
        stmt = stmt.order_by(Reminder.due_at.asc(), Reminder.id.asc()).limit(page.limit + 1)
        return list((await self.session.scalars(stmt)).all())

    async def delete_reminder(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            delete(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
        )
        return bool(getattr(result, "rowcount", 0))

    async def delete_reminders_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(delete(Reminder).where(Reminder.user_id == user_id))
        return int(getattr(result, "rowcount", 0) or 0)

    async def add_run(self, run: SkillRun) -> None:
        self.session.add(run)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
