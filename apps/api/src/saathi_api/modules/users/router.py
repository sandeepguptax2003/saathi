from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from saathi_api.core.rate_limit import limit_default
from saathi_api.core.schemas import ERROR_RESPONSES, Envelope, ok
from saathi_api.core.security import CurrentUser
from saathi_api.deps import get_users_service
from saathi_api.modules.users.schemas import MeOut, MePatch
from saathi_api.modules.users.service import UsersService

router = APIRouter(tags=["users"], dependencies=[Depends(limit_default)], responses=ERROR_RESPONSES)

UsersSvc = Annotated[UsersService, Depends(get_users_service)]


@router.get("/me")
async def get_me(user: CurrentUser, svc: UsersSvc) -> Envelope[MeOut]:
    return ok(await svc.get_or_create(user))


@router.patch("/me")
async def patch_me(user: CurrentUser, svc: UsersSvc, body: MePatch) -> Envelope[MeOut]:
    return ok(await svc.update(user, body))
