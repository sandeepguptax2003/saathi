"""Skill plugin interface + registry. A skill never performs side effects itself: anything that
sends, books or pays is returned as a pending action for the approval gate."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel

from saathi_api.modules.approvals.schemas import PendingActionOut
from saathi_api.modules.skills.schemas import ReminderIn, ReminderOut


class ActionProposer(Protocol):
    async def create(
        self,
        user_id: uuid.UUID,
        *,
        skill: str,
        action_type: str,
        payload: dict[str, Any],
        summary: str,
        commit: bool = True,
    ) -> PendingActionOut: ...


class ReminderStore(Protocol):
    async def create(
        self, user_id: uuid.UUID, body: ReminderIn, *, commit: bool = True
    ) -> ReminderOut: ...
    async def upcoming(self, user_id: uuid.UUID, limit: int) -> list[ReminderOut]: ...


@dataclass(frozen=True, slots=True)
class SkillContext:
    user_id: uuid.UUID
    now: datetime
    timezone: str
    locale: str
    approvals: ActionProposer
    reminders: ReminderStore


@dataclass(slots=True)
class SkillOutput:
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    pending_actions: list[PendingActionOut] = field(default_factory=list)


class Skill(Protocol):
    name: ClassVar[str]
    description: ClassVar[str]
    requires_approval: ClassVar[bool]
    runnable_via_api: ClassVar[bool]
    input_model: ClassVar[type[BaseModel]]

    async def run(self, ctx: SkillContext, args: BaseModel) -> SkillOutput: ...


def expect_args[M: BaseModel](args: BaseModel, model: type[M]) -> M:
    """Narrow the registry-validated args to the skill's own model."""
    if not isinstance(args, model):
        raise TypeError(f"expected {model.__name__}, got {type(args).__name__}")
    return args


class SkillRegistry:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = {s.name: s for s in skills}

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def catalog(self) -> str:
        """Compact description for the router prompt."""
        lines = []
        for s in self._skills.values():
            args = sorted(s.input_model.model_json_schema().get("properties", {}))
            lines.append(f"- {s.name}: {s.description} args={args}")
        return "\n".join(lines)


def default_registry() -> SkillRegistry:
    from saathi_api.modules.skills.builtins import (  # noqa: PLC0415 - avoid import cycle
        BillsSkill,
        CalendarSkill,
        DailyBriefSkill,
        EmailTriageSkill,
        RemindersSkill,
    )

    return SkillRegistry(
        [DailyBriefSkill(), RemindersSkill(), EmailTriageSkill(), CalendarSkill(), BillsSkill()]
    )
