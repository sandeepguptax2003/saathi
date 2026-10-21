"""Async Alembic env. URL from DATABASE_URL only (normalized to postgresql+asyncpg)."""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from saathi_api.core.db import Base
from saathi_api.modules.approvals import models as _approvals  # noqa: F401
from saathi_api.modules.assistant import models as _assistant  # noqa: F401
from saathi_api.modules.budget import models as _budget  # noqa: F401
from saathi_api.modules.memory import models as _memory  # noqa: F401
from saathi_api.modules.privacy import models as _privacy  # noqa: F401
from saathi_api.modules.skills import models as _skills  # noqa: F401
from saathi_api.modules.users import models as _users  # noqa: F401

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # statement_cache_size=0 keeps migrations working through the Supabase pooler too.
    engine = create_async_engine(_url(), connect_args={"statement_cache_size": 0})
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
