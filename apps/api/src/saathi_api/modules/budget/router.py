from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from saathi_api.core.rate_limit import limit_default
from saathi_api.core.schemas import ERROR_RESPONSES, Envelope, ok
from saathi_api.core.security import CurrentUser
from saathi_api.deps import get_budget_service, get_users_service
from saathi_api.modules.budget.schemas import BudgetUsageOut, UsageRange
from saathi_api.modules.budget.service import BudgetService
from saathi_api.modules.users.service import UsersService

router = APIRouter(
    prefix="/budget",
    tags=["budget"],
    dependencies=[Depends(limit_default)],
    responses=ERROR_RESPONSES,
)


@router.get("/usage")
async def get_budget_usage(
    user: CurrentUser,
    budget: Annotated[BudgetService, Depends(get_budget_service)],
    users: Annotated[UsersService, Depends(get_users_service)],
    range_: Annotated[UsageRange, Query(alias="range")] = "day",
) -> Envelope[BudgetUsageOut]:
    profile = await users.get_or_create(user)
    return ok(await budget.usage(user.id, profile.daily_budget_usd, range_))
