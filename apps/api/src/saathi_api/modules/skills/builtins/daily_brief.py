from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from saathi_api.modules.skills.builtins.bills import BillsArgs, BillsSkill
from saathi_api.modules.skills.builtins.calendar import CalendarArgs, CalendarSkill
from saathi_api.modules.skills.builtins.email_triage import EmailTriageArgs, EmailTriageSkill
from saathi_api.modules.skills.builtins.reminders import RemindersArgs, RemindersSkill
from saathi_api.modules.skills.registry import SkillContext, SkillOutput


class DailyBriefArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")


class DailyBriefSkill:
    name: ClassVar[str] = "daily-brief"
    description: ClassVar[str] = "Today's brief: calendar, bills due, important emails, reminders"
    requires_approval: ClassVar[bool] = False
    runnable_via_api: ClassVar[bool] = True
    input_model: ClassVar[type[BaseModel]] = DailyBriefArgs

    async def run(self, ctx: SkillContext, args: BaseModel) -> SkillOutput:  # noqa: ARG002
        cal = await CalendarSkill().run(ctx, CalendarArgs(days=1))
        bills = await BillsSkill().run(ctx, BillsArgs(action="list"))
        mail = await EmailTriageSkill().run(ctx, EmailTriageArgs(action="triage"))
        rem = await RemindersSkill().run(ctx, RemindersArgs(action="list"))
        return SkillOutput(
            summary=" ".join([cal.summary, bills.summary, mail.summary, rem.summary]),
            data={
                "calendar": cal.data,
                "bills": bills.data,
                "email": mail.data,
                "reminders": rem.data,
            },
        )
