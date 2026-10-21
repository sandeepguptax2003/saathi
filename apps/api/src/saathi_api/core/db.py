"""Async SQLAlchemy engine/session, declarative base and RLS-aware session dependency."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from saathi_api.core.config import Settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    # Python-side defaults so values are known after flush (no async lazy refresh needed);
    # server defaults keep raw SQL inserts correct too.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


class Database:
    """Owns the engine. Created once per app; connects lazily on first use."""

    def __init__(self, settings: Settings) -> None:
        connect_args: dict[str, Any] = {"server_settings": {"application_name": settings.app_name}}
        if settings.db_pgbouncer:
            # Supabase pooler in transaction mode cannot keep prepared statements.
            connect_args["statement_cache_size"] = 0
            connect_args["prepared_statement_cache_size"] = 0
        self.settings = settings
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
        )
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self, *, user_id: uuid.UUID | None = None) -> AsyncIterator[AsyncSession]:
        """Session scope. Rolls back on error; callers commit explicitly via repositories."""
        async with self.sessionmaker() as session:
            try:
                if user_id is not None:
                    await apply_rls_claims(session, user_id, enforce=self.settings.db_enforce_rls)
                yield session
            except BaseException:
                await session.rollback()
                raise

    async def ping(self) -> bool:
        async with self.engine.connect() as conn:
            await conn.execute(text("select 1"))
        return True

    async def dispose(self) -> None:
        await self.engine.dispose()


async def apply_rls_claims(session: AsyncSession, user_id: uuid.UUID, *, enforce: bool) -> None:
    """Expose the caller to Postgres so auth.uid() based RLS policies apply.

    Transaction-local, so it is safe with pooled connections. When `enforce` is off the API
    still filters every query by user_id (defense in depth either way).
    """
    claims = json.dumps({"sub": str(user_id), "role": "authenticated"})
    await session.execute(
        text(
            "select set_config('request.jwt.claims', :claims, true),"
            " set_config('request.jwt.claim.sub', :sub, true)"
        ),
        {"claims": claims, "sub": str(user_id)},
    )
    if enforce:
        await session.execute(text("set local role authenticated"))
