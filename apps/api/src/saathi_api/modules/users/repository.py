from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.modules.users.models import User


class UsersRepository(Protocol):
    async def get(self, user_id: uuid.UUID) -> User | None: ...
    async def create_if_missing(self, user_id: uuid.UUID, *, is_demo: bool) -> User: ...
    async def commit(self) -> None: ...


class SqlUsersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def create_if_missing(self, user_id: uuid.UUID, *, is_demo: bool) -> User:
        stmt = (
            insert(User)
            .values(id=user_id, is_demo=is_demo, locale="hi-IN", timezone="Asia/Kolkata")
            .on_conflict_do_nothing(index_elements=[User.id])
        )
        await self.session.execute(stmt)
        user = await self.session.get(User, user_id, populate_existing=True)
        if user is None:  # pragma: no cover - insert-or-ignore then select cannot miss
            raise RuntimeError("user upsert failed")
        return user

    async def commit(self) -> None:
        await self.session.commit()
