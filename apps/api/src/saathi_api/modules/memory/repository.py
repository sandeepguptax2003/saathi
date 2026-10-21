from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.core.pagination import PageParams
from saathi_api.modules.memory.models import Memory


class MemoryRepository(Protocol):
    async def add(self, memory: Memory) -> Memory: ...
    async def get(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> Memory | None: ...
    async def list_page(
        self, user_id: uuid.UUID, kind: str | None, page: PageParams
    ) -> list[Memory]: ...
    async def search(
        self, user_id: uuid.UUID, embedding: list[float], kind: str | None, limit: int
    ) -> list[tuple[Memory, float]]: ...
    async def soft_delete(self, memory: Memory) -> None: ...
    async def hard_delete(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> bool: ...
    async def commit(self) -> None: ...


class SqlMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, memory: Memory) -> Memory:
        self.session.add(memory)
        await self.session.flush()
        await self.session.refresh(memory)
        return memory

    async def get(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> Memory | None:
        stmt = select(Memory).where(
            Memory.id == memory_id, Memory.user_id == user_id, Memory.deleted_at.is_(None)
        )
        return (await self.session.scalars(stmt)).first()

    async def list_page(
        self, user_id: uuid.UUID, kind: str | None, page: PageParams
    ) -> list[Memory]:
        stmt = select(Memory).where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
        if kind:
            stmt = stmt.where(Memory.kind == kind)
        if page.cursor:
            c = page.cursor
            stmt = stmt.where(
                or_(Memory.created_at < c.ts, and_(Memory.created_at == c.ts, Memory.id < c.id))
            )
        stmt = stmt.order_by(Memory.created_at.desc(), Memory.id.desc()).limit(page.limit + 1)
        return list((await self.session.scalars(stmt)).all())

    async def search(
        self, user_id: uuid.UUID, embedding: list[float], kind: str | None, limit: int
    ) -> list[tuple[Memory, float]]:
        distance = Memory.embedding.cosine_distance(embedding)
        stmt = (
            select(Memory, distance.label("distance"))
            .where(
                Memory.user_id == user_id,
                Memory.deleted_at.is_(None),
                Memory.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(limit)
        )
        if kind:
            stmt = stmt.where(Memory.kind == kind)
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], 1.0 - float(row[1])) for row in rows]

    async def soft_delete(self, memory: Memory) -> None:
        memory.deleted_at = datetime.now(UTC)
        await self.session.flush()

    async def hard_delete(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            delete(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        )
        return bool(getattr(result, "rowcount", 0))

    async def commit(self) -> None:
        await self.session.commit()
