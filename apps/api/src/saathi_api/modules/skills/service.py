from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from saathi_api.core.crypto import EncryptedBlob, Encryptor
from saathi_api.core.errors import (
    AppError,
    Forbidden,
    NotFound,
    ValidationFailed,
    validation_issues,
)
from saathi_api.core.logging import get_logger
from saathi_api.core.pagination import PageParams, encode_cursor
from saathi_api.modules.approvals.models import PendingAction
from saathi_api.modules.approvals.repository import ApprovalsRepository
from saathi_api.modules.skills.models import Reminder, SkillRun
from saathi_api.modules.skills.registry import (
    ActionProposer,
    SkillContext,
    SkillOutput,
    SkillRegistry,
)
from saathi_api.modules.skills.repository import SkillsRepository
from saathi_api.modules.skills.schemas import (
    DemoResetOut,
    ReminderDeletedOut,
    ReminderIn,
    ReminderOut,
    ReminderPatch,
    SkillInfo,
    SkillRunOut,
)
from saathi_api.modules.users.schemas import MeOut
from saathi_api.seed import loader

log = get_logger(__name__)
REMINDER_PURPOSE = "reminder"


class RemindersService:
    def __init__(self, repo: SkillsRepository, encryptor: Encryptor) -> None:
        self.repo = repo
        self.enc = encryptor

    def _out(self, r: Reminder) -> ReminderOut:
        text = self.enc.decrypt_str(
            r.user_id,
            EncryptedBlob(r.text_ciphertext, r.nonce, r.key_version),
            purpose=REMINDER_PURPOSE,
        )
        return ReminderOut(
            id=r.id,
            text=text,
            due_at=r.due_at,
            status=r.status,  # type: ignore[arg-type]
            repeat_rule=r.repeat_rule,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )

    async def create(
        self, user_id: uuid.UUID, body: ReminderIn, *, commit: bool = True
    ) -> ReminderOut:
        if body.due_at.tzinfo is None:
            raise ValidationFailed(
                "dueAt must include a timezone offset", details={"field": "dueAt"}
            )
        blob = self.enc.encrypt(user_id, body.text, purpose=REMINDER_PURPOSE)
        reminder = await self.repo.add_reminder(
            Reminder(
                user_id=user_id,
                text_ciphertext=blob.ciphertext,
                nonce=blob.nonce,
                key_version=blob.key_version,
                due_at=body.due_at,
                status="pending",
                repeat_rule=body.repeat_rule,
            )
        )
        if commit:
            await self.repo.commit()
        return self._out(reminder)

    async def list_page(
        self, user_id: uuid.UUID, status: str | None, page: PageParams
    ) -> tuple[list[ReminderOut], str | None]:
        rows = await self.repo.list_reminders(user_id, status, page)
        next_cursor = None
        if len(rows) > page.limit:
            rows = rows[: page.limit]
            next_cursor = encode_cursor(rows[-1].due_at, rows[-1].id)
        return [self._out(r) for r in rows], next_cursor

    async def upcoming(self, user_id: uuid.UUID, limit: int) -> list[ReminderOut]:
        items, _ = await self.list_page(user_id, "pending", PageParams(cursor=None, limit=limit))
        return items

    async def update(
        self, user_id: uuid.UUID, reminder_id: uuid.UUID, patch: ReminderPatch
    ) -> ReminderOut:
        r = await self.repo.get_reminder(user_id, reminder_id)
        if r is None:
            raise NotFound("Reminder not found")
        if patch.text is not None:
            blob = self.enc.encrypt(user_id, patch.text, purpose=REMINDER_PURPOSE)
            r.text_ciphertext, r.nonce, r.key_version = (
                blob.ciphertext,
                blob.nonce,
                blob.key_version,
            )
        if patch.due_at is not None:
            r.due_at = patch.due_at
        if patch.status is not None:
            r.status = patch.status
        if "repeat_rule" in patch.model_fields_set:
            r.repeat_rule = patch.repeat_rule
        await self.repo.commit()
        return self._out(r)

    async def delete(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> ReminderDeletedOut:
        if not await self.repo.delete_reminder(user_id, reminder_id):
            raise NotFound("Reminder not found")
        await self.repo.commit()
        return ReminderDeletedOut(id=reminder_id)


class SimulatedExecutor:
    """Executes approved actions against demo data only. Never sends, books or pays for real."""

    async def execute(
        self,
        action: PendingAction,
        payload: dict[str, Any],  # noqa: ARG002 - real executors will use it
    ) -> dict[str, Any]:
        messages = {
            "bill_payment": "Payment simulated (demo): no money moved.",
            "send_email": "Email send simulated (demo): nothing left your inbox.",
        }
        message = messages.get(action.action_type, "Action simulated (demo).")
        return {"simulated": True, "actionType": action.action_type, "message": message}


class SkillsService:
    def __init__(
        self,
        registry: SkillRegistry,
        repo: SkillsRepository,
        approvals: ActionProposer,
        reminders: RemindersService,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.registry = registry
        self.repo = repo
        self.approvals = approvals
        self.reminders = reminders
        self.clock = clock

    def catalog(self) -> list[SkillInfo]:
        return [
            SkillInfo(
                name=s.name,
                description=s.description,
                requires_approval=s.requires_approval,
                runnable=s.runnable_via_api,
                input_schema=s.input_model.model_json_schema(),
            )
            for s in self.registry.all()
        ]

    def context(self, user: MeOut) -> SkillContext:
        return SkillContext(
            user_id=user.id,
            now=self.clock(),
            timezone=user.timezone,
            locale=user.locale,
            approvals=self.approvals,
            reminders=self.reminders,
        )

    async def execute(
        self, user: MeOut, name: str, args: dict[str, Any], *, via_api: bool, commit: bool = True
    ) -> SkillOutput:
        skill = self.registry.get(name)
        if skill is None:
            raise NotFound(f"Unknown skill '{name}'")
        if via_api and not skill.runnable_via_api:
            raise Forbidden(f"Skill '{name}' is not runnable directly")
        try:
            parsed = skill.input_model.model_validate(args)
        except ValidationError as exc:
            raise ValidationFailed(
                "Invalid skill args", details={"issues": validation_issues(exc.errors())}
            ) from exc
        started = time.perf_counter()
        status, error_code = "ok", None
        try:
            return await skill.run(self.context(user), parsed)
        except AppError as exc:
            status, error_code = "error", exc.code
            raise
        except Exception:
            status, error_code = "error", "internal_error"
            raise
        finally:
            await self.repo.add_run(
                SkillRun(
                    user_id=user.id,
                    skill=name,
                    status=status,
                    error_code=error_code,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            )
            if commit:
                await self.repo.commit()

    async def run_via_api(self, user: MeOut, name: str, args: dict[str, Any]) -> SkillRunOut:
        out = await self.execute(user, name, args, via_api=True)
        return SkillRunOut(
            skill=name, summary=out.summary, data=out.data, pending_actions=out.pending_actions
        )


class DemoService:
    def __init__(self, approvals_repo: ApprovalsRepository, skills_repo: SkillsRepository) -> None:
        self.approvals_repo = approvals_repo
        self.skills_repo = skills_repo

    async def reset(self, user: MeOut) -> DemoResetOut:
        """Demo users only. Seed inbox/calendar/bills are static JSON (dates relative to now), so
        reset clears the user's demo state: pending actions and reminders."""
        if not user.is_demo:
            raise Forbidden("Demo reset is only available for demo sessions")
        cleared = {
            "pendingActions": await self.approvals_repo.delete_for_user(user.id),
            "reminders": await self.skills_repo.delete_reminders_for_user(user.id),
        }
        await self.skills_repo.commit()
        log.info("demo_reset", **cleared)
        return DemoResetOut(cleared=cleared, seeded=loader.demo_counts())
