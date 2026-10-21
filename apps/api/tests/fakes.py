"""In-memory repositories implementing the module Protocols, for DB-free unit/API tests."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from saathi_api.core.pagination import PageParams
from saathi_api.modules.approvals.models import AuditLog, PendingAction
from saathi_api.modules.assistant.models import Conversation, Message
from saathi_api.modules.budget.models import LlmUsage
from saathi_api.modules.budget.repository import ModelUsageRow
from saathi_api.modules.memory.models import Memory
from saathi_api.modules.privacy.models import PrivacyEvent
from saathi_api.modules.skills.models import Reminder, SkillRun
from saathi_api.modules.users.models import User


def stamp(obj: Any) -> Any:
    now = datetime.now(UTC)
    if getattr(obj, "id", None) is None:
        obj.id = uuid.uuid4()
    if getattr(obj, "created_at", None) is None:
        obj.created_at = now
    obj.updated_at = now
    return obj


class Committable:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeUsersRepo(Committable):
    def __init__(self) -> None:
        super().__init__()
        self.rows: dict[uuid.UUID, User] = {}

    async def get(self, user_id: uuid.UUID) -> User | None:
        return self.rows.get(user_id)

    async def create_if_missing(self, user_id: uuid.UUID, *, is_demo: bool) -> User:
        if user_id not in self.rows:
            self.rows[user_id] = stamp(
                User(
                    id=user_id,
                    is_demo=is_demo,
                    locale="hi-IN",
                    timezone="Asia/Kolkata",
                    display_name=None,
                    voice_pref=None,
                    daily_budget_usd=None,
                )
            )
        return self.rows[user_id]


class FakeBudgetRepo(Committable):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[LlmUsage] = []

    async def add(self, usage: LlmUsage) -> None:
        self.rows.append(stamp(usage))

    async def total_cost(self, since: datetime, user_id: uuid.UUID | None = None) -> Decimal:
        return sum(
            (
                r.cost_usd
                for r in self.rows
                if r.created_at >= since and (user_id is None or r.user_id == user_id)
            ),
            Decimal(0),
        )

    async def by_model(self, user_id: uuid.UUID, since: datetime) -> list[ModelUsageRow]:
        agg: dict[str, list[Any]] = {}
        for r in self.rows:
            if r.user_id == user_id and r.created_at >= since:
                a = agg.setdefault(r.model, [0, 0, 0, Decimal(0)])
                a[0] += 1
                a[1] += r.tokens_in
                a[2] += r.tokens_out
                a[3] += r.cost_usd
        return [ModelUsageRow(m, *v) for m, v in sorted(agg.items())]


class FakePrivacyRepo(Committable):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[PrivacyEvent] = []

    async def add(self, event: PrivacyEvent) -> PrivacyEvent:
        self.rows.append(stamp(event))
        return event

    async def list_page(self, user_id: uuid.UUID, page: PageParams) -> list[PrivacyEvent]:
        return [r for r in reversed(self.rows) if r.user_id == user_id][: page.limit + 1]


class FakeApprovalsRepo(Committable):
    def __init__(self) -> None:
        super().__init__()
        self.rows: dict[uuid.UUID, PendingAction] = {}
        self.audits: list[AuditLog] = []

    async def add(self, action: PendingAction) -> PendingAction:
        stamp(action)
        self.rows[action.id] = action
        return action

    async def get_for_update(
        self, user_id: uuid.UUID, action_id: uuid.UUID
    ) -> PendingAction | None:
        a = self.rows.get(action_id)
        return a if a is not None and a.user_id == user_id else None

    async def get_by_idempotency_key(self, key: str) -> PendingAction | None:
        return next((a for a in self.rows.values() if a.idempotency_key == key), None)

    async def list_page(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> list[PendingAction]:
        rows = [
            a
            for a in self.rows.values()
            if a.user_id == user_id and (status is None or a.status == status)
        ]
        return sorted(rows, key=lambda a: a.created_at, reverse=True)[: page.limit + 1]

    async def expire_stale(self, user_id: uuid.UUID, now: datetime) -> int:
        n = 0
        for a in self.rows.values():
            if a.user_id == user_id and a.status == "pending" and a.expires_at < now:
                a.status = "expired"
                n += 1
        return n

    async def delete_for_user(self, user_id: uuid.UUID) -> int:
        ids = [k for k, a in self.rows.items() if a.user_id == user_id]
        for k in ids:
            del self.rows[k]
        return len(ids)

    async def audit(self, entry: AuditLog) -> None:
        self.audits.append(stamp(entry))


class FakeSkillsRepo(Committable):
    def __init__(self) -> None:
        super().__init__()
        self.reminders: dict[uuid.UUID, Reminder] = {}
        self.runs: list[SkillRun] = []

    async def add_reminder(self, reminder: Reminder) -> Reminder:
        stamp(reminder)
        self.reminders[reminder.id] = reminder
        return reminder

    async def get_reminder(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder | None:
        r = self.reminders.get(reminder_id)
        return r if r is not None and r.user_id == user_id else None

    async def list_reminders(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> list[Reminder]:
        rows = [
            r
            for r in self.reminders.values()
            if r.user_id == user_id and (status is None or r.status == status)
        ]
        return sorted(rows, key=lambda r: r.due_at)[: page.limit + 1]

    async def delete_reminder(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> bool:
        return self.reminders.pop(reminder_id, None) is not None

    async def delete_reminders_for_user(self, user_id: uuid.UUID) -> int:
        ids = [k for k, r in self.reminders.items() if r.user_id == user_id]
        for k in ids:
            del self.reminders[k]
        return len(ids)

    async def add_run(self, run: SkillRun) -> None:
        self.runs.append(stamp(run))


class FakeAssistantRepo(Committable):
    def __init__(self) -> None:
        super().__init__()
        self.conversations: dict[uuid.UUID, Conversation] = {}
        self.messages: list[Message] = []

    async def add_conversation(self, conv: Conversation) -> Conversation:
        stamp(conv)
        self.conversations[conv.id] = conv
        return conv

    async def get_conversation(self, user_id: uuid.UUID, conv_id: uuid.UUID) -> Conversation | None:
        c = self.conversations.get(conv_id)
        return c if c is not None and c.user_id == user_id else None

    async def list_conversations(self, user_id: uuid.UUID, page: PageParams) -> list[Conversation]:
        rows = [c for c in self.conversations.values() if c.user_id == user_id]
        return sorted(rows, key=lambda c: c.last_message_at, reverse=True)[: page.limit + 1]

    async def delete_conversation(self, user_id: uuid.UUID, conv_id: uuid.UUID) -> bool:
        if await self.get_conversation(user_id, conv_id) is None:
            return False
        del self.conversations[conv_id]
        self.messages = [m for m in self.messages if m.conversation_id != conv_id]
        return True

    async def add_message(self, msg: Message) -> Message:
        self.messages.append(stamp(msg))
        return msg

    async def list_messages(
        self, user_id: uuid.UUID, conv_id: uuid.UUID, page: PageParams
    ) -> list[Message]:
        return [m for m in reversed(self.messages) if m.conversation_id == conv_id][
            : page.limit + 1
        ]

    async def recent_messages(self, conv_id: uuid.UUID, limit: int) -> list[Message]:
        return [m for m in self.messages if m.conversation_id == conv_id][-limit:]


class FakeMemoryRepo(Committable):
    def __init__(self) -> None:
        super().__init__()
        self.rows: dict[uuid.UUID, Memory] = {}

    async def add(self, memory: Memory) -> Memory:
        stamp(memory)
        self.rows[memory.id] = memory
        return memory

    async def get(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> Memory | None:
        m = self.rows.get(memory_id)
        return m if m is not None and m.user_id == user_id and m.deleted_at is None else None

    async def list_page(
        self, user_id: uuid.UUID, kind: str | None, page: PageParams
    ) -> list[Memory]:
        rows = [
            m
            for m in self.rows.values()
            if m.user_id == user_id and m.deleted_at is None and (kind is None or m.kind == kind)
        ]
        return sorted(rows, key=lambda m: m.created_at, reverse=True)[: page.limit + 1]

    async def search(
        self, user_id: uuid.UUID, embedding: list[float], kind: str | None, limit: int
    ) -> list[tuple[Memory, float]]:
        def cos(a: list[float], b: list[float]) -> float:
            na = math.sqrt(sum(x * x for x in a)) or 1
            nb = math.sqrt(sum(x * x for x in b)) or 1
            return sum(x * y for x, y in zip(a, b, strict=True)) / (na * nb)

        rows = [
            m
            for m in await self.list_page(user_id, kind, PageParams(None, 100))
            if m.embedding is not None
        ]
        scored = sorted(
            ((m, cos(m.embedding or [], embedding)) for m in rows), key=lambda t: t[1], reverse=True
        )
        return scored[:limit]

    async def soft_delete(self, memory: Memory) -> None:
        memory.deleted_at = datetime.now(UTC)

    async def hard_delete(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> bool:
        return self.rows.pop(memory_id, None) is not None


class FakeDB:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    async def ping(self) -> bool:
        if not self.healthy:
            raise ConnectionError("db down")
        return True

    async def dispose(self) -> None:
        return None


class Store:
    """One shared set of fake repos per test app."""

    def __init__(self) -> None:
        self.users = FakeUsersRepo()
        self.budget = FakeBudgetRepo()
        self.privacy = FakePrivacyRepo()
        self.approvals = FakeApprovalsRepo()
        self.skills = FakeSkillsRepo()
        self.assistant = FakeAssistantRepo()
        self.memory = FakeMemoryRepo()
