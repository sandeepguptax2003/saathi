from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from saathi_api.modules.skills.registry import SkillContext, SkillOutput, expect_args
from saathi_api.seed import loader

_PRIORITY = {"work": 0, "bills": 1, "personal": 2, "travel": 3, "promotions": 9}


class EmailTriageArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: Literal["triage", "reply"] = "triage"
    email_id: str | None = None
    reply_text: str | None = Field(default=None, max_length=2000)


class EmailTriageSkill:
    name: ClassVar[str] = "email-triage"
    description: ClassVar[str] = (
        "Sort the demo inbox by priority; 'reply' drafts a reply for approval"
    )
    requires_approval: ClassVar[bool] = True
    runnable_via_api: ClassVar[bool] = True
    input_model: ClassVar[type[BaseModel]] = EmailTriageArgs

    async def run(self, ctx: SkillContext, raw: BaseModel) -> SkillOutput:
        args = expect_args(raw, EmailTriageArgs)
        emails = loader.inbox(ctx.now)

        def rank(e: loader.DemoEmail) -> tuple[int, int, float]:
            label = min((_PRIORITY.get(lbl, 5) for lbl in e.labels), default=5)
            return (0 if e.needs_reply else 1, label, -e.received_at.timestamp())

        ordered = sorted(emails, key=rank)
        if args.action == "reply":
            target = next((e for e in emails if e.id == args.email_id), None) or next(
                (e for e in ordered if e.needs_reply), None
            )
            if target is None:
                return SkillOutput(summary="No email needs a reply right now.")
            body = args.reply_text or "Thanks, will share it shortly."
            action = await ctx.approvals.create(
                ctx.user_id,
                skill=self.name,
                action_type="send_email",
                payload={
                    "to": target.sender,
                    "subject": f"Re: {target.subject}",
                    "body": body,
                    "inReplyTo": target.id,
                    "simulated": True,
                },
                summary=f"Send reply to {target.sender_name}: “{body[:80]}”",
                commit=False,
            )
            return SkillOutput(
                summary=(
                    f"Reply to {target.sender_name} is ready. It is sent only after you approve."
                ),
                pending_actions=[action],
            )
        unread = [e for e in ordered if e.unread and "promotions" not in e.labels]
        return SkillOutput(
            summary=(
                f"{len(unread)} important unread emails. "
                f"Top: {unread[0].sender_name}: {unread[0].subject}"
                if unread
                else "Inbox is clear."
            ),
            data={
                "emails": [
                    {
                        "id": e.id,
                        "from": e.sender_name,
                        "subject": e.subject,
                        "labels": list(e.labels),
                        "unread": e.unread,
                        "needsReply": e.needs_reply,
                        "receivedAt": e.received_at.isoformat(),
                    }
                    for e in ordered
                ]
            },
        )
