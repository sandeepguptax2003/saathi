from __future__ import annotations

from typing import Any, ClassVar, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from saathi_api.core.errors import NotFound, Unprocessable
from saathi_api.modules.skills.registry import SkillContext, SkillOutput, expect_args
from saathi_api.seed import loader


class BillsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: Literal["list", "pay"] = "list"
    bill_id: str | None = None


class BillsSkill:
    name: ClassVar[str] = "bills"
    description: ClassVar[str] = (
        "List upcoming bills; 'pay' proposes a payment for approval (simulated)"
    )
    requires_approval: ClassVar[bool] = True
    runnable_via_api: ClassVar[bool] = True
    input_model: ClassVar[type[BaseModel]] = BillsArgs

    async def run(self, ctx: SkillContext, raw: BaseModel) -> SkillOutput:
        args = expect_args(raw, BillsArgs)
        today = ctx.now.astimezone(ZoneInfo(ctx.timezone)).date()
        items = loader.bills(ctx.now, ctx.timezone)
        unpaid: list[dict[str, Any]] = [
            {
                "id": b.id,
                "biller": b.biller,
                "amountInr": b.amount_inr,
                "amount": loader.format_inr(b.amount_inr),
                "dueDate": b.due_date.isoformat(),
                "daysLeft": (b.due_date - today).days,
                "overdue": b.due_date < today,
            }
            for b in items
        ]
        if args.action == "list":
            due_soon = [b for b in items if (b.due_date - today).days <= 7]
            total = sum(b.amount_inr for b in due_soon)
            return SkillOutput(
                summary=(
                    f"{len(due_soon)} bills due within 7 days, total {loader.format_inr(total)}."
                ),
                data={"bills": unpaid},
            )

        target = next((b for b in items if b.id == args.bill_id), None) if args.bill_id else None
        if target is None and args.bill_id is None:
            target = items[0] if items else None  # most urgent
        if target is None:
            raise NotFound("Bill not found") if args.bill_id else Unprocessable("No bills to pay")
        summary = (
            f"Pay {loader.format_inr(target.amount_inr)} to {target.biller} (UPI {target.payee})"
        )
        action = await ctx.approvals.create(
            ctx.user_id,
            skill=self.name,
            action_type="bill_payment",
            payload={
                "billId": target.id,
                "biller": target.biller,
                "amountInr": target.amount_inr,
                "payee": target.payee,
                "accountRef": target.account_ref,
                "simulated": True,
            },
            summary=summary,
            commit=False,
        )
        return SkillOutput(
            summary=(
                f"Payment ready for your approval: {summary}. "
                "Nothing is paid until you tap Approve."
            ),
            data={"billId": target.id},
            pending_actions=[action],
        )
