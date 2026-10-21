from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from saathi_api.core.schemas import CamelModel

ActionStatus = Literal["pending", "approved", "rejected", "expired", "executed", "failed"]
Decision = Literal["approve", "reject"]


class PendingActionOut(CamelModel):
    id: uuid.UUID
    skill: str
    action_type: str
    summary: str
    status: ActionStatus
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime


class DecisionOut(CamelModel):
    action: PendingActionOut
    replayed: bool = False
    result: dict[str, Any] | None = None
