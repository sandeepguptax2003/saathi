"""Approval gate with Idempotency-Key semantics.

approve/reject(key):
- same key + same decision within the replay window  -> replay the stored outcome (no re-execution)
- action already decided with another key / decision  -> 409 conflict
- key already used on another action                  -> 409 conflict
- pending but past expires_at                         -> marked expired, 409 conflict
Payloads are sealed with AES-GCM (purpose "pending_action"); only `summary` is plaintext.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from saathi_api.core.crypto import Encryptor
from saathi_api.core.errors import Conflict, NotFound, ValidationFailed
from saathi_api.core.logging import get_logger
from saathi_api.core.pagination import PageParams, encode_cursor
from saathi_api.modules.approvals.models import AuditLog, PendingAction
from saathi_api.modules.approvals.repository import ApprovalsRepository
from saathi_api.modules.approvals.schemas import Decision, DecisionOut, PendingActionOut

log = get_logger(__name__)
PURPOSE = "pending_action"
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_APPROVE_STATES = {"approved", "executed", "failed"}


class ActionExecutor(Protocol):
    async def execute(self, action: PendingAction, payload: dict[str, Any]) -> dict[str, Any]: ...


class ApprovalService:
    def __init__(
        self,
        repo: ApprovalsRepository,
        encryptor: Encryptor,
        executor: ActionExecutor,
        *,
        ttl: timedelta = timedelta(minutes=30),
        replay_window: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.repo = repo
        self.enc = encryptor
        self.executor = executor
        self.ttl = ttl
        self.replay_window = replay_window
        self.clock = clock

    async def create(
        self,
        user_id: uuid.UUID,
        *,
        skill: str,
        action_type: str,
        payload: dict[str, Any],
        summary: str,
        commit: bool = True,
    ) -> PendingActionOut:
        sealed = self.enc.seal(user_id, json.dumps(payload, ensure_ascii=False), purpose=PURPOSE)
        action = await self.repo.add(
            PendingAction(
                user_id=user_id,
                skill=skill,
                action_type=action_type,
                payload_ciphertext=sealed,
                summary=summary,
                status="pending",
                expires_at=self.clock() + self.ttl,
            )
        )
        await self.repo.audit(
            AuditLog(
                user_id=user_id,
                actor="system",
                event="action_proposed",
                entity="pending_action",
                entity_id=action.id,
                metadata_={"skill": skill, "actionType": action_type},
            )
        )
        if commit:
            await self.repo.commit()
        return PendingActionOut.model_validate(action)

    async def list_page(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> tuple[list[PendingActionOut], str | None]:
        if await self.repo.expire_stale(user_id, self.clock()):
            await self.repo.commit()
        rows = await self.repo.list_page(user_id, status, page)
        next_cursor = None
        if len(rows) > page.limit:
            rows = rows[: page.limit]
            next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id)
        return [PendingActionOut.model_validate(r) for r in rows], next_cursor

    async def decide(
        self,
        user_id: uuid.UUID,
        action_id: uuid.UUID,
        decision: Decision,
        idempotency_key: str | None,
    ) -> DecisionOut:
        if not idempotency_key or not IDEMPOTENCY_KEY_RE.match(idempotency_key):
            raise ValidationFailed(
                "Idempotency-Key header required (8-128 chars, [A-Za-z0-9._:-])",
                details={"header": "Idempotency-Key"},
            )
        now = self.clock()
        action = await self.repo.get_for_update(user_id, action_id)
        if action is None:
            raise NotFound("Pending action not found")

        if action.idempotency_key is not None:
            return self._replay_or_conflict(action, decision, idempotency_key, now)

        other = await self.repo.get_by_idempotency_key(idempotency_key)
        if other is not None and other.id != action.id:
            raise Conflict("Idempotency-Key already used for another action")

        if action.status != "pending":
            raise Conflict(f"Action is {action.status}", details={"status": action.status})
        if action.expires_at <= now:
            action.status = "expired"
            await self.repo.commit()
            raise Conflict("Action expired; ask Saathi again", details={"status": "expired"})

        action.idempotency_key = idempotency_key
        action.decided_at = now
        result: dict[str, Any] | None = None
        if decision == "reject":
            action.status = "rejected"
            await self._audit(action, "action_rejected", {})
        else:
            action.status = "approved"
            await self._audit(action, "action_approved", {})
            payload: dict[str, Any] = json.loads(
                self.enc.open(user_id, action.payload_ciphertext, purpose=PURPOSE)
            )
            try:
                result = await self.executor.execute(action, payload)
                action.status = "executed"
                await self._audit(
                    action, "action_executed", {"simulated": bool(result.get("simulated"))}
                )
            except Exception as exc:
                log.warning("action_execute_failed", skill=action.skill, error=type(exc).__name__)
                action.status = "failed"
                await self._audit(action, "action_failed", {"error": type(exc).__name__})
        await self.repo.commit()
        return DecisionOut(
            action=PendingActionOut.model_validate(action), replayed=False, result=result
        )

    def _replay_or_conflict(
        self, action: PendingAction, decision: Decision, key: str, now: datetime
    ) -> DecisionOut:
        same_decision = (decision == "approve" and action.status in _APPROVE_STATES) or (
            decision == "reject" and action.status == "rejected"
        )
        fresh = action.decided_at is not None and now - action.decided_at <= self.replay_window
        if action.idempotency_key == key and same_decision and fresh:
            return DecisionOut(action=PendingActionOut.model_validate(action), replayed=True)
        raise Conflict(f"Action already {action.status}", details={"status": action.status})

    async def _audit(self, action: PendingAction, event: str, meta: dict[str, Any]) -> None:
        await self.repo.audit(
            AuditLog(
                user_id=action.user_id,
                actor="user",
                event=event,
                entity="pending_action",
                entity_id=action.id,
                metadata_={"skill": action.skill, **meta},
            )
        )
