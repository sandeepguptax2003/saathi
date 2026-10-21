from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from saathi_api.core.pagination import PageParams, page_params
from saathi_api.core.rate_limit import limit_default
from saathi_api.core.schemas import ERROR_RESPONSES, Envelope, ok
from saathi_api.core.security import CurrentUser
from saathi_api.deps import get_approval_service
from saathi_api.modules.approvals.schemas import ActionStatus, DecisionOut, PendingActionOut
from saathi_api.modules.approvals.service import ApprovalService

router = APIRouter(
    prefix="/pending-actions",
    tags=["approvals"],
    dependencies=[Depends(limit_default)],
    responses=ERROR_RESPONSES,
)
ApprovalSvc = Annotated[ApprovalService, Depends(get_approval_service)]
IdemKey = Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)]


@router.get("")
async def list_pending_actions(
    user: CurrentUser,
    svc: ApprovalSvc,
    page: Annotated[PageParams, Depends(page_params)],
    status: ActionStatus | None = None,
) -> Envelope[list[PendingActionOut]]:
    items, cursor = await svc.list_page(user.id, status, page)
    return ok(items, next_cursor=cursor)


@router.post("/{action_id}/approve")
async def approve_action(
    user: CurrentUser,
    svc: ApprovalSvc,
    action_id: uuid.UUID,
    response: Response,
    idempotency_key: IdemKey = None,
) -> Envelope[DecisionOut]:
    out = await svc.decide(user.id, action_id, "approve", idempotency_key)
    response.headers["Idempotent-Replayed"] = str(out.replayed).lower()
    return ok(out)


@router.post("/{action_id}/reject")
async def reject_action(
    user: CurrentUser,
    svc: ApprovalSvc,
    action_id: uuid.UUID,
    response: Response,
    idempotency_key: IdemKey = None,
) -> Envelope[DecisionOut]:
    out = await svc.decide(user.id, action_id, "reject", idempotency_key)
    response.headers["Idempotent-Replayed"] = str(out.replayed).lower()
    return ok(out)
