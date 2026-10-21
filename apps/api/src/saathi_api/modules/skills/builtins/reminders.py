from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import ClassVar, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from saathi_api.modules.skills.registry import SkillContext, SkillOutput, expect_args
from saathi_api.modules.skills.schemas import ReminderIn


class RemindersArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: Literal["create", "list"] = "list"
    text: str | None = Field(default=None, max_length=500)
    due_at: datetime | None = None


def guess_due(text: str, now: datetime, tz: str) -> datetime:
    """Tiny heuristic until the router extracts dueAt: 'kal/tomorrow' -> 09:00 next day, else +1h.

    TODO(llm): have Nano return ISO dueAt in args (prompted with the user's tz) and drop this.
    """
    zone = ZoneInfo(tz)
    local = now.astimezone(zone)
    lowered = text.lower()
    if any(w in lowered for w in ("kal", "tomorrow")):
        return datetime.combine(local.date() + timedelta(days=1), time(9, 0), tzinfo=zone)
    return now + timedelta(hours=1)


class RemindersSkill:
    name: ClassVar[str] = "reminders"
    description: ClassVar[str] = "Create or list reminders (stored encrypted)"
    requires_approval: ClassVar[bool] = False
    runnable_via_api: ClassVar[bool] = False
    input_model: ClassVar[type[BaseModel]] = RemindersArgs

    async def run(self, ctx: SkillContext, raw: BaseModel) -> SkillOutput:
        args = expect_args(raw, RemindersArgs)
        if args.action == "create" and args.text:
            due = args.due_at or guess_due(args.text, ctx.now, ctx.timezone)
            created = await ctx.reminders.create(
                ctx.user_id, ReminderIn(text=args.text, due_at=due), commit=False
            )
            local = created.due_at.astimezone(ZoneInfo(ctx.timezone))
            return SkillOutput(
                summary=f"Reminder set for {local:%a %d %b, %H:%M}.",
                data={"reminderId": str(created.id), "dueAt": created.due_at.isoformat()},
            )
        items = await ctx.reminders.upcoming(ctx.user_id, 5)
        return SkillOutput(
            summary=f"{len(items)} upcoming reminders.",
            data={"reminders": [{"id": str(r.id), "dueAt": r.due_at.isoformat()} for r in items]},
        )
