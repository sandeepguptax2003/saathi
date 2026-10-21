from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.modules.budget.models import LlmUsage


@dataclass(frozen=True, slots=True)
class ModelUsageRow:
    model: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal


class BudgetRepository(Protocol):
    async def add(self, usage: LlmUsage) -> None: ...
    async def total_cost(self, since: datetime, user_id: uuid.UUID | None = None) -> Decimal: ...
    async def by_model(self, user_id: uuid.UUID, since: datetime) -> list[ModelUsageRow]: ...
    async def commit(self) -> None: ...


class SqlBudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, usage: LlmUsage) -> None:
        self.session.add(usage)
        await self.session.flush()

    async def total_cost(self, since: datetime, user_id: uuid.UUID | None = None) -> Decimal:
        stmt = select(func.coalesce(func.sum(LlmUsage.cost_usd), 0)).where(
            LlmUsage.created_at >= since
        )
        if user_id is not None:
            stmt = stmt.where(LlmUsage.user_id == user_id)
        value = await self.session.scalar(stmt)
        return Decimal(value or 0)

    async def by_model(self, user_id: uuid.UUID, since: datetime) -> list[ModelUsageRow]:
        stmt = (
            select(
                LlmUsage.model,
                func.count(),
                func.coalesce(func.sum(LlmUsage.tokens_in), 0),
                func.coalesce(func.sum(LlmUsage.tokens_out), 0),
                func.coalesce(func.sum(LlmUsage.cost_usd), 0),
            )
            .where(LlmUsage.user_id == user_id, LlmUsage.created_at >= since)
            .group_by(LlmUsage.model)
            .order_by(LlmUsage.model)
        )
        rows = (await self.session.execute(stmt)).all()
        return [ModelUsageRow(r[0], int(r[1]), int(r[2]), int(r[3]), Decimal(r[4])) for r in rows]

    async def commit(self) -> None:
        await self.session.commit()
