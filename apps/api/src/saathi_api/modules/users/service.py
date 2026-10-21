from __future__ import annotations

from decimal import Decimal

from saathi_api.core.config import Settings
from saathi_api.core.errors import ValidationFailed
from saathi_api.core.security import AuthUser
from saathi_api.modules.users.models import User
from saathi_api.modules.users.repository import UsersRepository
from saathi_api.modules.users.schemas import MeOut, MePatch


class UsersService:
    def __init__(self, repo: UsersRepository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings

    async def get_or_create_model(self, auth: AuthUser) -> User:
        user = await self.repo.get(auth.id)
        if user is None:
            user = await self.repo.create_if_missing(auth.id, is_demo=auth.is_anonymous)
            await self.repo.commit()
        return user

    async def get_or_create(self, auth: AuthUser) -> MeOut:
        return MeOut.model_validate(await self.get_or_create_model(auth))

    async def update(self, auth: AuthUser, patch: MePatch) -> MeOut:
        user = await self.get_or_create_model(auth)
        changes = patch.model_dump(exclude_unset=True, by_alias=False)
        if "daily_budget_usd" in changes and changes["daily_budget_usd"] is not None:
            if changes["daily_budget_usd"] > self.settings.daily_budget_usd:
                raise ValidationFailed(
                    f"dailyBudgetUsd cannot exceed {self.settings.daily_budget_usd}",
                    details={"field": "dailyBudgetUsd", "max": self.settings.daily_budget_usd},
                )
            changes["daily_budget_usd"] = Decimal(str(changes["daily_budget_usd"]))
        for key, value in changes.items():
            if value is None and key in {"locale", "timezone"}:
                continue
            setattr(user, key, value)
        await self.repo.commit()
        return MeOut.model_validate(user)
