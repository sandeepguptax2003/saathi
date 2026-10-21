from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from saathi_api.core.config import ModelPrice
from saathi_api.core.errors import BudgetExceeded
from saathi_api.modules.budget.service import BudgetService, compute_cost
from tests.conftest import make_settings
from tests.fakes import FakeBudgetRepo


def svc(**kw: object) -> tuple[BudgetService, FakeBudgetRepo]:
    repo = FakeBudgetRepo()
    return BudgetService(repo, make_settings(**kw)), repo


def test_cost_uses_per_million_prices() -> None:
    # Nano: $0.06 in / $0.24 out per 1M
    assert compute_cost(ModelPrice(0.06, 0.24), 1_000_000, 1_000_000) == Decimal("0.300000")
    assert compute_cost(ModelPrice(0.30, 0.90), 1000, 500) == Decimal("0.000750")


async def test_record_and_usage_breakdown() -> None:
    s, _ = svc()
    uid = uuid.uuid4()
    await s.record(
        user_id=uid,
        model=s.settings.model_fast,
        tokens_in=1000,
        tokens_out=1000,
        escalated=False,
        request_id="r1",
    )
    await s.record(
        user_id=uid,
        model=s.settings.model_reasoning,
        tokens_in=1000,
        tokens_out=1000,
        escalated=True,
        request_id="r1",
    )
    usage = await s.usage(uid, None, "day")
    assert usage.spent_usd == pytest.approx(0.00030 + 0.00120)
    assert {m.model for m in usage.by_model} == {s.settings.model_fast, s.settings.model_reasoning}
    assert usage.cap_usd == 1.0 and not usage.alert


async def test_unknown_model_is_charged_conservatively() -> None:
    s, _ = svc()
    assert s.cost_for("some/unknown", 1_000_000, 0) == Decimal("3.000000")


async def test_user_cap_blocks_with_retry_after() -> None:
    s, repo = svc(daily_budget_usd=0.01, global_daily_budget_usd=5)
    uid = uuid.uuid4()
    await s.ensure_within_budget(uid, None)  # fresh user passes
    await s.record(
        user_id=uid,
        model=s.settings.model_reasoning,
        tokens_in=20_000,
        tokens_out=5_000,
        escalated=True,
        request_id=None,
    )
    with pytest.raises(BudgetExceeded) as exc:
        await s.ensure_within_budget(uid, None)
    assert exc.value.status_code == 429 and exc.value.code == "budget_exceeded"
    assert exc.value.details["scope"] == "user"
    assert 0 < int(exc.value.headers["Retry-After"]) <= 86400
    await s.ensure_within_budget(uuid.uuid4(), None)  # other users unaffected


async def test_global_cap_blocks_everyone() -> None:
    s, _ = svc(daily_budget_usd=1, global_daily_budget_usd=1)
    for _ in range(2):
        await s.record(
            user_id=uuid.uuid4(),
            model=s.settings.model_reasoning,
            tokens_in=1_000_000,
            tokens_out=300_000,
            escalated=False,
            request_id=None,
        )
    with pytest.raises(BudgetExceeded) as exc:
        await s.ensure_within_budget(uuid.uuid4(), None)
    assert exc.value.details["scope"] == "global"


async def test_user_cap_cannot_exceed_server_cap() -> None:
    s, _ = svc(daily_budget_usd=1)
    assert s.user_cap(50) == Decimal("1")
    assert s.user_cap(0.25) == Decimal("0.25")


def test_day_starts_at_ist_midnight() -> None:
    s, _ = svc()
    now = datetime(2026, 10, 21, 3, 0, tzinfo=UTC)  # 08:30 IST
    assert s.day_start(now) == datetime(2026, 10, 20, 18, 30, tzinfo=UTC)
    assert s.seconds_until_reset(now) == ((15 * 60 + 30) * 60)
