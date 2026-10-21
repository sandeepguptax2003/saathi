from __future__ import annotations

from typing import Literal

from saathi_api.core.schemas import CamelModel

UsageRange = Literal["day", "week"]


class ModelUsageOut(CamelModel):
    model: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float


class BudgetUsageOut(CamelModel):
    range: UsageRange
    spent_usd: float
    cap_usd: float
    remaining_usd: float
    alert: bool
    global_cap_reached: bool
    by_model: list[ModelUsageOut]
