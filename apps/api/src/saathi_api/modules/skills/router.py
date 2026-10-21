from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from saathi_api.core.pagination import PageParams, page_params
from saathi_api.core.rate_limit import limit_default
from saathi_api.core.schemas import ERROR_RESPONSES, Envelope, ok
from saathi_api.core.security import CurrentUser
from saathi_api.deps import (
    get_demo_service,
    get_reminders_service,
    get_skills_service,
    get_users_service,
)
from saathi_api.modules.skills.schemas import (
    DemoResetOut,
    ReminderDeletedOut,
    ReminderIn,
    ReminderOut,
    ReminderPatch,
    ReminderStatus,
    SkillInfo,
    SkillRunIn,
    SkillRunOut,
)
from saathi_api.modules.skills.service import DemoService, RemindersService, SkillsService
from saathi_api.modules.users.service import UsersService

router = APIRouter(dependencies=[Depends(limit_default)], responses=ERROR_RESPONSES)

SkillsSvc = Annotated[SkillsService, Depends(get_skills_service)]
RemindersSvc = Annotated[RemindersService, Depends(get_reminders_service)]
UsersSvc = Annotated[UsersService, Depends(get_users_service)]


@router.get("/skills", tags=["skills"])
async def list_skills(_user: CurrentUser, svc: SkillsSvc) -> Envelope[list[SkillInfo]]:
    return ok(svc.catalog())


@router.post("/skills/{name}/run", tags=["skills"])
async def run_skill(
    user: CurrentUser, svc: SkillsSvc, users: UsersSvc, name: str, body: SkillRunIn
) -> Envelope[SkillRunOut]:
    """Runnable: daily-brief, email-triage, bills. Side effects come back as pending actions."""
    me = await users.get_or_create(user)
    return ok(await svc.run_via_api(me, name, body.args))


@router.get("/reminders", tags=["reminders"])
async def list_reminders(
    user: CurrentUser,
    svc: RemindersSvc,
    page: Annotated[PageParams, Depends(page_params)],
    status: ReminderStatus | None = None,
) -> Envelope[list[ReminderOut]]:
    items, cursor = await svc.list_page(user.id, status, page)
    return ok(items, next_cursor=cursor)


@router.post("/reminders", tags=["reminders"], status_code=status.HTTP_201_CREATED)
async def create_reminder(
    user: CurrentUser, svc: RemindersSvc, users: UsersSvc, body: ReminderIn
) -> Envelope[ReminderOut]:
    await users.get_or_create(user)
    return ok(await svc.create(user.id, body))


@router.patch("/reminders/{reminder_id}", tags=["reminders"])
async def update_reminder(
    user: CurrentUser, svc: RemindersSvc, reminder_id: uuid.UUID, body: ReminderPatch
) -> Envelope[ReminderOut]:
    return ok(await svc.update(user.id, reminder_id, body))


@router.delete("/reminders/{reminder_id}", tags=["reminders"])
async def delete_reminder(
    user: CurrentUser, svc: RemindersSvc, reminder_id: uuid.UUID
) -> Envelope[ReminderDeletedOut]:
    return ok(await svc.delete(user.id, reminder_id))


@router.post("/demo/reset", tags=["demo"])
async def reset_demo(
    user: CurrentUser, users: UsersSvc, demo: Annotated[DemoService, Depends(get_demo_service)]
) -> Envelope[DemoResetOut]:
    return ok(await demo.reset(await users.get_or_create(user)))
