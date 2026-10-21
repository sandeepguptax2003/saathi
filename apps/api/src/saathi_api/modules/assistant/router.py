from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from saathi_api.core.pagination import PageParams, page_params
from saathi_api.core.rate_limit import limit_default, limit_turns
from saathi_api.core.schemas import ERROR_RESPONSES, Envelope, ok
from saathi_api.core.security import CurrentUser
from saathi_api.deps import AssistantFactory, get_assistant_factory, get_assistant_service
from saathi_api.modules.assistant.schemas import (
    ConversationDeletedOut,
    ConversationOut,
    MessageOut,
    TurnIn,
)
from saathi_api.modules.assistant.service import AssistantService

router = APIRouter(responses=ERROR_RESPONSES)
AssistantSvc = Annotated[AssistantService, Depends(get_assistant_service)]

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


@router.post(
    "/assistant/turns",
    tags=["assistant"],
    dependencies=[Depends(limit_turns)],
    response_class=StreamingResponse,
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE stream of turn events"}
    },
)
async def create_turn(
    user: CurrentUser,
    body: TurnIn,
    factory: Annotated[AssistantFactory, Depends(get_assistant_factory)],
) -> StreamingResponse:
    """Events: meta, privacy, token, tool, pending_action, done, error.

    Budget/validation/conversation errors happen before the stream opens and return the
    normal JSON error envelope; failures after that arrive as an `error` event.
    """
    stack = AsyncExitStack()
    try:
        service = await stack.enter_async_context(factory(user))
        prepared = await service.prepare_turn(user, body)
    except BaseException:
        await stack.aclose()
        raise

    async def events() -> AsyncIterator[bytes]:
        async with stack:
            async for event in service.stream_turn(prepared):
                yield event.encode()

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/conversations", tags=["conversations"], dependencies=[Depends(limit_default)])
async def list_conversations(
    user: CurrentUser, svc: AssistantSvc, page: Annotated[PageParams, Depends(page_params)]
) -> Envelope[list[ConversationOut]]:
    items, cursor = await svc.list_conversations(user.id, page)
    return ok(items, next_cursor=cursor)


@router.get(
    "/conversations/{conversation_id}/messages",
    tags=["conversations"],
    dependencies=[Depends(limit_default)],
)
async def list_messages(
    user: CurrentUser,
    svc: AssistantSvc,
    conversation_id: uuid.UUID,
    page: Annotated[PageParams, Depends(page_params)],
) -> Envelope[list[MessageOut]]:
    items, cursor = await svc.list_messages(user.id, conversation_id, page)
    return ok(items, next_cursor=cursor)


@router.delete(
    "/conversations/{conversation_id}",
    tags=["conversations"],
    dependencies=[Depends(limit_default)],
)
async def delete_conversation(
    user: CurrentUser, svc: AssistantSvc, conversation_id: uuid.UUID
) -> Envelope[ConversationDeletedOut]:
    return ok(await svc.delete_conversation(user.id, conversation_id))
