from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from saathi_api.core.pagination import PageParams, page_params
from saathi_api.core.rate_limit import limit_default
from saathi_api.core.schemas import ERROR_RESPONSES, Envelope, ok
from saathi_api.core.security import CurrentUser
from saathi_api.deps import get_privacy_service
from saathi_api.modules.privacy.schemas import PrivacyEventOut, PrivacyPreviewIn, PrivacyPreviewOut
from saathi_api.modules.privacy.service import PrivacyService

router = APIRouter(
    prefix="/privacy",
    tags=["privacy"],
    dependencies=[Depends(limit_default)],
    responses=ERROR_RESPONSES,
)

PrivacySvc = Annotated[PrivacyService, Depends(get_privacy_service)]


@router.get("/events")
async def list_privacy_events(
    user: CurrentUser, svc: PrivacySvc, page: Annotated[PageParams, Depends(page_params)]
) -> Envelope[list[PrivacyEventOut]]:
    items, cursor = await svc.list_events(user.id, page)
    return ok(items, next_cursor=cursor)


@router.post("/preview")
async def preview_masking(
    _user: CurrentUser, body: PrivacyPreviewIn
) -> Envelope[PrivacyPreviewOut]:
    """What the model would see for this text. Pure, nothing stored."""
    return ok(PrivacyService.preview(body))
