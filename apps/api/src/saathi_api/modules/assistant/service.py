"""Turn orchestration.

prepare_turn (before the stream opens, so failures are plain JSON errors):
  user -> budget guard -> conversation -> mask user text -> persist masked message + privacy event
stream_turn (SSE):
  meta -> privacy -> route (Nano, escalate to Super) -> [tool -> skill -> pending_action*]
  -> reply stream (masked prompt; unmasked locally per delta) -> persist -> done | error
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from saathi_api.core.config import Settings
from saathi_api.core.context import current_request_id
from saathi_api.core.errors import AppError, NotFound
from saathi_api.core.logging import get_logger
from saathi_api.core.pagination import PageParams, encode_cursor
from saathi_api.core.security import AuthUser
from saathi_api.modules.assistant.models import Conversation, Message
from saathi_api.modules.assistant.repository import AssistantRepository
from saathi_api.modules.assistant.schemas import (
    ConversationDeletedOut,
    ConversationOut,
    MessageOut,
    SseEvent,
    TurnIn,
    TurnUsageOut,
)
from saathi_api.modules.budget.service import BudgetService
from saathi_api.modules.llm.schemas import ChatMessage, StreamUsage, Tier
from saathi_api.modules.llm.service import LLMService
from saathi_api.modules.privacy.masker import MaskSession, StreamUnmasker, unmask
from saathi_api.modules.privacy.service import PrivacyService
from saathi_api.modules.skills.service import SkillsService
from saathi_api.modules.users.schemas import MeOut
from saathi_api.modules.users.service import UsersService

log = get_logger(__name__)
HISTORY_LIMIT = 8

SYSTEM_PROMPT = """You are Saathi, a warm, concise Hindi-English (Hinglish) voice assistant for
Indian users. Reply in {language}, in 1-3 short spoken sentences. Placeholders like <PHONE_1> stand
for private data: keep them exactly as written, never guess what they hide. You never send, book or
pay anything yourself: when an action is pending, tell the user to tap Approve.{context}"""


class TurnUsageRecorder:
    """Records each LLM call through BudgetService and keeps per-turn totals for the done event."""

    def __init__(self, budget: BudgetService) -> None:
        self.budget = budget
        self.cost = Decimal(0)
        self.tokens_in = 0
        self.tokens_out = 0
        self.escalated = False

    async def record(
        self,
        *,
        user_id: uuid.UUID | None,
        model: str,
        tokens_in: int,
        tokens_out: int,
        escalated: bool,
        request_id: str | None,
    ) -> Decimal:
        cost = await self.budget.record(
            user_id=user_id,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            escalated=escalated,
            request_id=request_id,
        )
        self.cost += cost
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.escalated = self.escalated or escalated
        return cost


@dataclass
class PreparedTurn:
    me: MeOut
    conversation: Conversation
    mask: MaskSession
    masked_text: str
    entity_counts: dict[str, int]
    history: list[Message] = field(default_factory=list)


def _unmask_args(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, str):
        return unmask(value, mapping)
    if isinstance(value, dict):
        return {k: _unmask_args(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_unmask_args(v, mapping) for v in value]
    return value


class AssistantService:
    def __init__(
        self,
        *,
        repo: AssistantRepository,
        users: UsersService,
        budget: BudgetService,
        privacy: PrivacyService,
        skills: SkillsService,
        llm: LLMService,
        usage: TurnUsageRecorder,
        settings: Settings,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repo = repo
        self.users = users
        self.budget = budget
        self.privacy = privacy
        self.skills = skills
        self.llm = llm
        self.usage = usage
        self.settings = settings
        self.clock = clock

    # ------------------------------------------------------------------ turn
    async def prepare_turn(self, auth: AuthUser, body: TurnIn) -> PreparedTurn:
        me = await self.users.get_or_create(auth)
        await self.budget.ensure_within_budget(me.id, me.daily_budget_usd)
        now = self.clock()

        mask = MaskSession()  # TODO(memory): seed known_names from the user's 'person' memories
        masked = mask.mask(body.text)

        if body.conversation_id is not None:
            conv = await self.repo.get_conversation(me.id, body.conversation_id)
            if conv is None:
                raise NotFound("Conversation not found")
        else:
            conv = await self.repo.add_conversation(
                Conversation(user_id=me.id, title=masked.masked_text[:60], last_message_at=now)
            )
        history = await self.repo.recent_messages(conv.id, HISTORY_LIMIT)
        msg = await self.repo.add_message(
            Message(
                conversation_id=conv.id,
                user_id=me.id,
                role="user",
                content_masked=masked.masked_text,
            )
        )
        await self.privacy.record(me.id, masked.entity_counts, msg.id)
        conv.last_message_at = now
        await self.repo.commit()
        me = me.model_copy(update={"locale": body.locale})
        return PreparedTurn(me, conv, mask, masked.masked_text, masked.entity_counts, history)

    async def stream_turn(self, turn: PreparedTurn) -> AsyncIterator[SseEvent]:
        yield SseEvent(
            "meta", {"conversationId": str(turn.conversation.id), "model": self.settings.model_fast}
        )
        yield SseEvent("privacy", {"entityCounts": turn.entity_counts})
        stream_usage = StreamUsage(model=self.settings.model_fast)
        try:
            decision = await self.llm.route(turn.masked_text, self.skills.registry.catalog())
            tier: Tier = "reasoning" if decision.needs_reasoning or decision.escalated else "fast"
            stream_usage.escalated = decision.escalated
            context = ""
            if decision.intent == "skill" and decision.skill:
                yield SseEvent("tool", {"skill": decision.skill, "status": "running"})
                try:
                    out = await self.skills.execute(
                        turn.me,
                        decision.skill,
                        _unmask_args(decision.args, turn.mask.mapping),
                        via_api=False,
                        commit=False,
                    )
                except AppError as exc:
                    yield SseEvent(
                        "tool", {"skill": decision.skill, "status": "failed", "code": exc.code}
                    )
                    context = (
                        f"\nThe {decision.skill} skill failed ({exc.code}). Apologise briefly."
                    )
                    tier = "reasoning"  # escalate on tool failure
                else:
                    yield SseEvent("tool", {"skill": decision.skill, "status": "done"})
                    for action in out.pending_actions:
                        yield SseEvent(
                            "pending_action", {"id": str(action.id), "summary": action.summary}
                        )
                    # Skill output can contain PII from demo data: mask before the model sees it.
                    safe_summary = turn.mask.mask(out.summary).masked_text
                    context = f"\nSkill result ({decision.skill}): {safe_summary}"

            language = (
                "Hinglish (Roman script)" if turn.me.locale == "hi-IN" else "simple Indian English"
            )
            messages = [
                ChatMessage("system", SYSTEM_PROMPT.format(language=language, context=context)),
                *[
                    ChatMessage("assistant" if m.role == "assistant" else "user", m.content_masked)
                    for m in turn.history
                    if m.role in {"user", "assistant"}
                ],
                ChatMessage("user", turn.masked_text),
            ]
            unmasker = StreamUnmasker(turn.mask.mapping)
            produced: list[str] = []
            async for delta in self.llm.stream(messages, tier=tier, usage=stream_usage):
                produced.append(delta)
                text = unmasker.feed(delta)
                if text:
                    yield SseEvent("token", {"delta": text})
            tail = unmasker.flush()
            if tail:
                yield SseEvent("token", {"delta": tail})

            await self.repo.add_message(
                Message(
                    conversation_id=turn.conversation.id,
                    user_id=turn.me.id,
                    role="assistant",
                    content_masked="".join(produced),
                    model=stream_usage.model,
                    tokens_in=stream_usage.tokens_in,
                    tokens_out=stream_usage.tokens_out,
                    latency_ms=stream_usage.latency_ms,
                )
            )
            turn.conversation.last_message_at = self.clock()
            await self.repo.commit()
            usage = TurnUsageOut(
                model=stream_usage.model,
                tokens_in=self.usage.tokens_in,
                tokens_out=self.usage.tokens_out,
                cost_usd=float(self.usage.cost),
                escalated=self.usage.escalated,
                first_token_ms=stream_usage.first_token_ms,
                latency_ms=stream_usage.latency_ms,
            )
            yield SseEvent("done", {"usage": usage.model_dump(by_alias=True)})
        except AppError as exc:
            await self._safe_commit()
            yield SseEvent(
                "error",
                {"code": exc.code, "message": exc.message, "requestId": current_request_id()},
            )
        except Exception:
            log.exception("turn_failed")
            await self._safe_commit()
            yield SseEvent(
                "error",
                {
                    "code": "internal_error",
                    "message": "Something went wrong",
                    "requestId": current_request_id(),
                },
            )

    async def _safe_commit(self) -> None:
        """Keep usage rows for calls that did happen, so the budget stays honest after failures."""
        try:
            await self.repo.commit()
        except Exception:  # pragma: no cover - best effort
            log.warning("turn_commit_failed")

    # ------------------------------------------------------------------ conversations
    async def list_conversations(
        self, user_id: uuid.UUID, page: PageParams
    ) -> tuple[list[ConversationOut], str | None]:
        rows = await self.repo.list_conversations(user_id, page)
        cursor = None
        if len(rows) > page.limit:
            rows = rows[: page.limit]
            cursor = encode_cursor(rows[-1].last_message_at, rows[-1].id)
        return [ConversationOut.model_validate(r) for r in rows], cursor

    async def list_messages(
        self, user_id: uuid.UUID, conv_id: uuid.UUID, page: PageParams
    ) -> tuple[list[MessageOut], str | None]:
        if await self.repo.get_conversation(user_id, conv_id) is None:
            raise NotFound("Conversation not found")
        rows = await self.repo.list_messages(user_id, conv_id, page)
        cursor = None
        if len(rows) > page.limit:
            rows = rows[: page.limit]
            cursor = encode_cursor(rows[-1].created_at, rows[-1].id)
        return [MessageOut.model_validate(r) for r in rows], cursor

    async def delete_conversation(
        self, user_id: uuid.UUID, conv_id: uuid.UUID
    ) -> ConversationDeletedOut:
        if not await self.repo.delete_conversation(user_id, conv_id):
            raise NotFound("Conversation not found")
        await self.repo.commit()
        return ConversationDeletedOut(id=conv_id)
