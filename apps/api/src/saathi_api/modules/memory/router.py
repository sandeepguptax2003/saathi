from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from saathi_api.core.pagination import PageParams, page_params
from saathi_api.core.rate_limit import limit_default
from saathi_api.core.schemas import ERROR_RESPONSES, Envelope, ok
from saathi_api.core.security import CurrentUser
from saathi_api.deps import get_memory_service
from saathi_api.modules.memory.schemas import (
    DeletedOut,
    MemoryIn,
    MemoryKind,
    MemoryOut,
    MemoryPatch,
)
from saathi_api.modules.memory.service import MemoryService

router = APIRouter(
    prefix="/memories",
    tags=["memory"],
    dependencies=[Depends(limit_default)],
    responses=ERROR_RESPONSES,
)
MemorySvc = Annotated[MemoryService, Depends(get_memory_service)]


@router.get("")
async def list_memories(
    user: CurrentUser,
    svc: MemorySvc,
    page: Annotated[PageParams, Depends(page_params)],
    kind: MemoryKind | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
) -> Envelope[list[MemoryOut]]:
    """List memories, or semantic search when `q` is given (no cursor for search results)."""
    if q:
        return ok(await svc.search(user.id, q, kind, page.limit))
    items, cursor = await svc.list_page(user.id, kind, page)
    return ok(items, next_cursor=cursor)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_memory(user: CurrentUser, svc: MemorySvc, body: MemoryIn) -> Envelope[MemoryOut]:
    return ok(await svc.create(user.id, body))


@router.patch("/{memory_id}")
async def update_memory(
    user: CurrentUser, svc: MemorySvc, memory_id: uuid.UUID, body: MemoryPatch
) -> Envelope[MemoryOut]:
    return ok(await svc.update(user.id, memory_id, body))


@router.delete("/{memory_id}")
async def delete_memory(
    user: CurrentUser, svc: MemorySvc, memory_id: uuid.UUID, hard: bool = False
) -> Envelope[DeletedOut]:
    return ok(await svc.delete(user.id, memory_id, hard=hard))
