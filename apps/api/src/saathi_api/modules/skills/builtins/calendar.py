from __future__ import annotations

from datetime import timedelta
from typing import ClassVar
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from saathi_api.modules.skills.registry import SkillContext, SkillOutput, expect_args
from saathi_api.seed import loader


class CalendarArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    days: int = Field(default=1, ge=1, le=14)


class CalendarSkill:
    name: ClassVar[str] = "calendar"
    description: ClassVar[str] = "Show today's (or the next N days') events from the demo calendar"
    requires_approval: ClassVar[bool] = False
    runnable_via_api: ClassVar[bool] = False
    input_model: ClassVar[type[BaseModel]] = CalendarArgs

    async def run(self, ctx: SkillContext, raw: BaseModel) -> SkillOutput:
        args = expect_args(raw, CalendarArgs)
        zone = ZoneInfo(ctx.timezone)
        today = ctx.now.astimezone(zone).date()
        horizon = today + timedelta(days=args.days)
        events = [
            e for e in loader.calendar(ctx.now, ctx.timezone) if today <= e.start.date() < horizon
        ]
        upcoming = [e for e in events if e.end >= ctx.now]
        data = [
            {
                "id": e.id,
                "title": e.title,
                "start": e.start.isoformat(),
                "end": e.end.isoformat(),
                "location": e.location,
            }
            for e in events
        ]
        if not upcoming:
            return SkillOutput(summary="No more events in this window.", data={"events": data})
        nxt = upcoming[0]
        return SkillOutput(
            summary=(
                f"{len(events)} events; next: {nxt.title} at {nxt.start.astimezone(zone):%H:%M}."
            ),
            data={"events": data},
        )
