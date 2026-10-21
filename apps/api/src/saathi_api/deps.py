"""Composition root: process-wide singletons (Services) + per-request service providers.

Routers depend on these providers; tests override them via app.dependency_overrides.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from saathi_api.core.config import Settings
from saathi_api.core.crypto import Encryptor
from saathi_api.core.db import Database
from saathi_api.core.rate_limit import RateLimiter
from saathi_api.core.security import AuthUser, CurrentUser
from saathi_api.modules.approvals.repository import SqlApprovalsRepository
from saathi_api.modules.approvals.service import ApprovalService
from saathi_api.modules.assistant.repository import SqlAssistantRepository
from saathi_api.modules.assistant.service import AssistantService, TurnUsageRecorder
from saathi_api.modules.budget.repository import SqlBudgetRepository
from saathi_api.modules.budget.service import BudgetService
from saathi_api.modules.llm.service import LLMClient, LLMService, UsageRecorder
from saathi_api.modules.memory.repository import SqlMemoryRepository
from saathi_api.modules.memory.service import MemoryService
from saathi_api.modules.privacy.repository import SqlPrivacyRepository
from saathi_api.modules.privacy.service import PrivacyService
from saathi_api.modules.skills.registry import SkillRegistry, default_registry
from saathi_api.modules.skills.repository import SqlSkillsRepository
from saathi_api.modules.skills.service import (
    DemoService,
    RemindersService,
    SimulatedExecutor,
    SkillsService,
)
from saathi_api.modules.users.repository import SqlUsersRepository
from saathi_api.modules.users.service import UsersService


@dataclass
class Services:
    settings: Settings
    db: Database
    http: httpx.AsyncClient
    llm: LLMClient
    encryptor: Encryptor
    rate_limiter: RateLimiter
    registry: SkillRegistry = field(default_factory=default_registry)


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]


async def get_session(services: ServicesDep, user: CurrentUser) -> AsyncIterator[AsyncSession]:
    async with services.db.session(user_id=user.id) as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------- builders
def build_users(session: AsyncSession, s: Services) -> UsersService:
    return UsersService(SqlUsersRepository(session), s.settings)


def build_budget(session: AsyncSession, s: Services) -> BudgetService:
    return BudgetService(SqlBudgetRepository(session), s.settings)


def build_approvals(session: AsyncSession, s: Services) -> ApprovalService:
    return ApprovalService(
        SqlApprovalsRepository(session),
        s.encryptor,
        SimulatedExecutor(),
        ttl=timedelta(minutes=s.settings.approval_ttl_minutes),
        replay_window=timedelta(hours=s.settings.idempotency_replay_hours),
    )


def build_skills(session: AsyncSession, s: Services) -> SkillsService:
    repo = SqlSkillsRepository(session)
    return SkillsService(
        s.registry, repo, build_approvals(session, s), RemindersService(repo, s.encryptor)
    )


def build_llm(s: Services, user: AuthUser, recorder: UsageRecorder | None) -> LLMService:
    return LLMService(s.llm, recorder, user_id=user.id)


def build_assistant(session: AsyncSession, s: Services, user: AuthUser) -> AssistantService:
    budget = build_budget(session, s)
    usage = TurnUsageRecorder(budget)
    return AssistantService(
        repo=SqlAssistantRepository(session),
        users=build_users(session, s),
        budget=budget,
        privacy=PrivacyService(SqlPrivacyRepository(session)),
        skills=build_skills(session, s),
        llm=build_llm(s, user, usage),
        usage=usage,
        settings=s.settings,
    )


# ---------------------------------------------------------------------------- providers
def get_users_service(session: SessionDep, services: ServicesDep) -> UsersService:
    return build_users(session, services)


def get_budget_service(session: SessionDep, services: ServicesDep) -> BudgetService:
    return build_budget(session, services)


def get_privacy_service(session: SessionDep) -> PrivacyService:
    return PrivacyService(SqlPrivacyRepository(session))


def get_memory_service(
    session: SessionDep, services: ServicesDep, user: CurrentUser
) -> MemoryService:
    llm = build_llm(services, user, build_budget(session, services))
    return MemoryService(SqlMemoryRepository(session), services.encryptor, llm)


def get_approval_service(session: SessionDep, services: ServicesDep) -> ApprovalService:
    return build_approvals(session, services)


def get_reminders_service(session: SessionDep, services: ServicesDep) -> RemindersService:
    return RemindersService(SqlSkillsRepository(session), services.encryptor)


def get_skills_service(session: SessionDep, services: ServicesDep) -> SkillsService:
    return build_skills(session, services)


def get_demo_service(session: SessionDep) -> DemoService:
    return DemoService(SqlApprovalsRepository(session), SqlSkillsRepository(session))


def get_assistant_service(
    session: SessionDep, services: ServicesDep, user: CurrentUser
) -> AssistantService:
    return build_assistant(session, services, user)


AssistantFactory = Callable[[AuthUser], AbstractAsyncContextManager[AssistantService]]


def get_assistant_factory(services: ServicesDep) -> AssistantFactory:
    """SSE turns outlive the request's dependency scope, so they open their own session."""

    @asynccontextmanager
    async def factory(user: AuthUser) -> AsyncIterator[AssistantService]:
        async with services.db.session(user_id=user.id) as session:
            yield build_assistant(session, services, user)

    return factory
