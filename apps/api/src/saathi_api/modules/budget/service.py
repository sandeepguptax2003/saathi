"""Budget guard. Cost = tokens x price; refuses new turns once user or global daily cap is hit."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from saathi_api.core.config import ModelPrice, Settings
from saathi_api.core.errors import BudgetExceeded
from saathi_api.core.logging import get_logger
from saathi_api.modules.budget.models import LlmUsage
from saathi_api.modules.budget.repository import BudgetRepository
from saathi_api.modules.budget.schemas import BudgetUsageOut, ModelUsageOut, UsageRange

log = get_logger(__name__)
_MICRO = Decimal("0.000001")
# Unknown model: charge like the most expensive configured one so the cap stays conservative.
_FALLBACK_PRICE = ModelPrice(3.0, 15.0)


def compute_cost(price: ModelPrice, tokens_in: int, tokens_out: int) -> Decimal:
    raw = (
        Decimal(tokens_in) * Decimal(str(price.input_per_m))
        + Decimal(tokens_out) * Decimal(str(price.output_per_m))
    ) / Decimal(1_000_000)
    return raw.quantize(_MICRO, rounding=ROUND_HALF_UP)


class BudgetService:
    def __init__(self, repo: BudgetRepository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings
        self.prices = settings.price_table()
        self.tz = ZoneInfo(settings.budget_timezone)

    # ---------------------------------------------------------------- time windows
    def day_start(self, now: datetime | None = None) -> datetime:
        local = (now or datetime.now(UTC)).astimezone(self.tz)
        return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)

    def seconds_until_reset(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        next_start = self.day_start(now) + timedelta(days=1)
        return max(1, int((next_start - now).total_seconds()))

    def user_cap(self, user_cap_usd: float | None) -> Decimal:
        cap = (
            self.settings.daily_budget_usd
            if user_cap_usd is None
            else min(user_cap_usd, self.settings.daily_budget_usd)
        )
        return Decimal(str(cap))

    # ---------------------------------------------------------------- guard
    async def ensure_within_budget(
        self, user_id: uuid.UUID, user_cap_usd: float | None, *, now: datetime | None = None
    ) -> None:
        since = self.day_start(now)
        global_spent = await self.repo.total_cost(since)
        if global_spent >= Decimal(str(self.settings.global_daily_budget_usd)):
            log.warning("budget_global_cap_hit", spent=str(global_spent))
            raise BudgetExceeded(
                "Saathi has hit today's shared AI budget. Please try again tomorrow.",
                retry_after_s=self.seconds_until_reset(now),
                details={"scope": "global"},
            )
        spent = await self.repo.total_cost(since, user_id)
        cap = self.user_cap(user_cap_usd)
        if spent >= cap:
            raise BudgetExceeded(
                "Aaj ka AI budget khatam ho gaya. Kal phir try karein.",
                retry_after_s=self.seconds_until_reset(now),
                details={"scope": "user", "capUsd": float(cap), "spentUsd": float(spent)},
            )

    # ---------------------------------------------------------------- recording
    def cost_for(self, model: str, tokens_in: int, tokens_out: int) -> Decimal:
        return compute_cost(self.prices.get(model, _FALLBACK_PRICE), tokens_in, tokens_out)

    async def record(
        self,
        *,
        user_id: uuid.UUID | None,
        model: str,
        tokens_in: int,
        tokens_out: int,
        escalated: bool,
        request_id: str | None,
    ) -> Decimal:
        cost = self.cost_for(model, tokens_in, tokens_out)
        await self.repo.add(
            LlmUsage(
                user_id=user_id,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                escalated=escalated,
                request_id=request_id,
            )
        )
        return cost

    # ---------------------------------------------------------------- dashboard
    async def usage(
        self, user_id: uuid.UUID, user_cap_usd: float | None, range_: UsageRange
    ) -> BudgetUsageOut:
        today = self.day_start()
        since = today if range_ == "day" else today - timedelta(days=6)
        rows = await self.repo.by_model(user_id, since)
        spent_today = await self.repo.total_cost(today, user_id)
        global_spent = await self.repo.total_cost(today)
        spent = sum((r.cost_usd for r in rows), Decimal(0))
        cap = self.user_cap(user_cap_usd) * (1 if range_ == "day" else 7)
        return BudgetUsageOut(
            range=range_,
            spent_usd=float(spent),
            cap_usd=float(cap),
            remaining_usd=float(max(Decimal(0), cap - spent)),
            alert=spent_today
            >= self.user_cap(user_cap_usd) * Decimal(str(self.settings.budget_alert_ratio)),
            global_cap_reached=global_spent >= Decimal(str(self.settings.global_daily_budget_usd)),
            by_model=[
                ModelUsageOut(
                    model=r.model,
                    calls=r.calls,
                    tokens_in=r.tokens_in,
                    tokens_out=r.tokens_out,
                    cost_usd=float(r.cost_usd),
                )
                for r in rows
            ],
        )
