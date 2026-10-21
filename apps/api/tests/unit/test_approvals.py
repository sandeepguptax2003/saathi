from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from saathi_api.core.crypto import Encryptor
from saathi_api.core.errors import Conflict, NotFound, ValidationFailed
from saathi_api.modules.approvals.models import PendingAction
from saathi_api.modules.approvals.service import ApprovalService
from tests.fakes import FakeApprovalsRepo


class CountingExecutor:
    def __init__(self, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    async def execute(self, action: PendingAction, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        return {"simulated": True, "amount": payload["amountInr"]}


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 21, 5, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def make(fail: bool = False) -> tuple[ApprovalService, FakeApprovalsRepo, CountingExecutor, Clock]:
    repo, ex, clock = FakeApprovalsRepo(), CountingExecutor(fail), Clock()
    svc = ApprovalService(
        repo, Encryptor({1: b"k" * 40}, 1), ex, ttl=timedelta(minutes=30), clock=clock
    )
    return svc, repo, ex, clock


async def _pending(svc: ApprovalService, uid: uuid.UUID) -> uuid.UUID:
    out = await svc.create(
        uid,
        skill="bills",
        action_type="bill_payment",
        payload={"amountInr": 1249, "payee": "bescom@okhdfcbank"},
        summary="Pay ₹1,249",
    )
    assert out.status == "pending"
    return out.id


async def test_payload_is_encrypted_at_rest() -> None:
    svc, repo, _, _ = make()
    aid = await _pending(svc, uuid.uuid4())
    assert b"bescom" not in repo.rows[aid].payload_ciphertext


async def test_approve_executes_once_and_replays_same_key() -> None:
    svc, repo, ex, _ = make()
    uid = uuid.uuid4()
    aid = await _pending(svc, uid)
    first = await svc.decide(uid, aid, "approve", "key-abc-123")
    assert first.action.status == "executed" and not first.replayed
    assert first.result == {"simulated": True, "amount": 1249}
    again = await svc.decide(uid, aid, "approve", "key-abc-123")
    assert again.replayed and again.action.status == "executed"
    assert ex.calls == 1
    assert [a.event for a in repo.audits] == [
        "action_proposed",
        "action_approved",
        "action_executed",
    ]


async def test_different_key_or_opposite_decision_conflicts() -> None:
    svc, _, _, _ = make()
    uid = uuid.uuid4()
    aid = await _pending(svc, uid)
    await svc.decide(uid, aid, "approve", "key-abc-123")
    with pytest.raises(Conflict):
        await svc.decide(uid, aid, "approve", "key-other-999")
    with pytest.raises(Conflict):
        await svc.decide(uid, aid, "reject", "key-abc-123")


async def test_reject_is_idempotent_and_never_executes() -> None:
    svc, _, ex, _ = make()
    uid = uuid.uuid4()
    aid = await _pending(svc, uid)
    assert (await svc.decide(uid, aid, "reject", "rej-key-0001")).action.status == "rejected"
    assert (await svc.decide(uid, aid, "reject", "rej-key-0001")).replayed
    assert ex.calls == 0


async def test_key_reuse_on_another_action_conflicts() -> None:
    svc, _, _, _ = make()
    uid = uuid.uuid4()
    a1, a2 = await _pending(svc, uid), await _pending(svc, uid)
    await svc.decide(uid, a1, "approve", "shared-key-1")
    with pytest.raises(Conflict):
        await svc.decide(uid, a2, "approve", "shared-key-1")


async def test_expired_action_cannot_be_approved() -> None:
    svc, repo, ex, clock = make()
    uid = uuid.uuid4()
    aid = await _pending(svc, uid)
    clock.now += timedelta(minutes=31)
    with pytest.raises(Conflict) as exc:
        await svc.decide(uid, aid, "approve", "late-key-01")
    assert exc.value.details == {"status": "expired"}
    assert repo.rows[aid].status == "expired" and ex.calls == 0


async def test_replay_window_closes_after_24h() -> None:
    svc, _, _, clock = make()
    uid = uuid.uuid4()
    aid = await _pending(svc, uid)
    await svc.decide(uid, aid, "approve", "key-abc-123")
    clock.now += timedelta(hours=25)
    with pytest.raises(Conflict):
        await svc.decide(uid, aid, "approve", "key-abc-123")


async def test_execution_failure_marks_failed() -> None:
    svc, _, _, _ = make(fail=True)
    uid = uuid.uuid4()
    aid = await _pending(svc, uid)
    out = await svc.decide(uid, aid, "approve", "key-abc-123")
    assert out.action.status == "failed"


async def test_key_required_and_ownership_enforced() -> None:
    svc, _, _, _ = make()
    uid = uuid.uuid4()
    aid = await _pending(svc, uid)
    with pytest.raises(ValidationFailed):
        await svc.decide(uid, aid, "approve", None)
    with pytest.raises(ValidationFailed):
        await svc.decide(uid, aid, "approve", "bad key!")
    with pytest.raises(NotFound):
        await svc.decide(uuid.uuid4(), aid, "approve", "key-abc-123")
