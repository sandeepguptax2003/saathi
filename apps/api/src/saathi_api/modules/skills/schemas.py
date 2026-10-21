from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from saathi_api.core.schemas import CamelModel
from saathi_api.modules.approvals.schemas import PendingActionOut

ReminderStatus = Literal["pending", "done", "cancelled"]


class SkillInfo(CamelModel):
    name: str
    description: str
    requires_approval: bool
    runnable: bool
    input_schema: dict[str, Any]


class SkillRunIn(CamelModel):
    args: dict[str, Any] = Field(default_factory=dict)


class SkillRunOut(CamelModel):
    skill: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    pending_actions: list[PendingActionOut] = Field(default_factory=list)


class ReminderIn(CamelModel):
    text: str = Field(min_length=1, max_length=500)
    due_at: datetime
    repeat_rule: str | None = Field(default=None, max_length=128, description="RFC 5545 RRULE")


class ReminderPatch(CamelModel):
    text: str | None = Field(default=None, min_length=1, max_length=500)
    due_at: datetime | None = None
    status: ReminderStatus | None = None
    repeat_rule: str | None = Field(default=None, max_length=128)


class ReminderOut(CamelModel):
    id: uuid.UUID
    text: str
    due_at: datetime
    status: ReminderStatus
    repeat_rule: str | None
    created_at: datetime
    updated_at: datetime


class ReminderDeletedOut(CamelModel):
    id: uuid.UUID
    deleted: bool = True


class DemoResetOut(CamelModel):
    reset: bool = True
    cleared: dict[str, int]
    seeded: dict[str, int]
