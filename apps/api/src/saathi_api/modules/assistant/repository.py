from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.core.pagination import PageParams
from saathi_api.modules.assistant.models import Conversation, Message


class AssistantRepository(Protocol):
    async def add_conversation(self, conv: Conversation) -> Conversation: ...
    async def get_conversation(
        self, user_id: uuid.UUID, conv_id: uuid.UUID
    ) -> Conversation | None: ...
    async def list_conversations(
        self, user_id: uuid.UUID, page: PageParams
    ) -> list[Conversation]: ...
    async def delete_conversation(self, user_id: uuid.UUID, conv_id: uuid.UUID) -> bool: ...
    async def add_message(self, msg: Message) -> Message: ...
    async def list_messages(
        self, user_id: uuid.UUID, conv_id: uuid.UUID, page: PageParams
    ) -> list[Message]: ...
    async def recent_messages(self, conv_id: uuid.UUID, limit: int) -> list[Message]: ...
    async def commit(self) -> None: ...


class SqlAssistantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_conversation(self, conv: Conversation) -> Conversation:
        self.session.add(conv)
        await self.session.flush()
        return conv

    async def get_conversation(self, user_id: uuid.UUID, conv_id: uuid.UUID) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == user_id
        )
        return (await self.session.scalars(stmt)).first()

    async def list_conversations(self, user_id: uuid.UUID, page: PageParams) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        if page.cursor:
            c = page.cursor
            stmt = stmt.where(
                or_(
                    Conversation.last_message_at < c.ts,
                    and_(Conversation.last_message_at == c.ts, Conversation.id < c.id),
                )
            )
        stmt = stmt.order_by(Conversation.last_message_at.desc(), Conversation.id.desc()).limit(
            page.limit + 1
        )
        return list((await self.session.scalars(stmt)).all())

    async def delete_conversation(self, user_id: uuid.UUID, conv_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            delete(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user_id)
        )
        return bool(getattr(result, "rowcount", 0))

    async def add_message(self, msg: Message) -> Message:
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def list_messages(
        self, user_id: uuid.UUID, conv_id: uuid.UUID, page: PageParams
    ) -> list[Message]:
        stmt = select(Message).where(Message.conversation_id == conv_id, Message.user_id == user_id)
        if page.cursor:
            c = page.cursor
            stmt = stmt.where(
                or_(Message.created_at < c.ts, and_(Message.created_at == c.ts, Message.id < c.id))
            )
        stmt = stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(page.limit + 1)
        return list((await self.session.scalars(stmt)).all())

    async def recent_messages(self, conv_id: uuid.UUID, limit: int) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        return list(reversed((await self.session.scalars(stmt)).all()))

    async def commit(self) -> None:
        await self.session.commit()
