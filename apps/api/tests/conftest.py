from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from saathi_api import deps
from saathi_api.core.config import Settings
from saathi_api.core.security import AuthUser, get_current_user
from saathi_api.deps import Services, get_services
from saathi_api.main import build_services, create_app
from saathi_api.modules.approvals.service import ApprovalService
from saathi_api.modules.assistant.service import AssistantService, TurnUsageRecorder
from saathi_api.modules.budget.service import BudgetService
from saathi_api.modules.llm.repository import MockBackend
from saathi_api.modules.llm.service import LLMService
from saathi_api.modules.memory.service import MemoryService
from saathi_api.modules.privacy.service import PrivacyService
from saathi_api.modules.skills.service import (
    DemoService,
    RemindersService,
    SimulatedExecutor,
    SkillsService,
)
from saathi_api.modules.users.service import UsersService
from tests.fakes import FakeDB, Store

JWT_SECRET = "test-jwt-secret-" + "x" * 32  # test-only value
PEPPER = "test-pepper-" + "y" * 32  # test-only value


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "env": "test",
        "llm_mock": True,
        "database_url": "postgresql://saathi:saathi@localhost:5432/saathi_test",
        "supabase_url": "http://localhost:54321",
        "supabase_jwt_secret": JWT_SECRET,
        "encryption_pepper": PEPPER,
        "cors_origins": ["http://localhost:3000"],
        "llm_retry_base_delay_s": 0.0,
        "_env_file": None,
    }
    base.update(overrides)
    return Settings(**base)


def make_token(user_id: uuid.UUID | None = None, *, anonymous: bool = True, **claims: Any) -> str:
    payload = {
        "sub": str(user_id or uuid.uuid4()),
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
        "is_anonymous": anonymous,
        **claims,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never read real config (e.g. a developer's NEBIUS_API_KEY) from the environment."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def store() -> Store:
    return Store()


@pytest.fixture
def backend() -> MockBackend:
    return MockBackend()


def install_fakes(app: FastAPI, store: Store) -> None:
    """Swap every DB-backed provider for one built on in-memory repos."""

    def users(s: Services) -> UsersService:
        return UsersService(store.users, s.settings)

    def budget(s: Services) -> BudgetService:
        return BudgetService(store.budget, s.settings)

    def approvals(s: Services) -> ApprovalService:
        return ApprovalService(
            store.approvals,
            s.encryptor,
            SimulatedExecutor(),
            ttl=timedelta(minutes=s.settings.approval_ttl_minutes),
        )

    def skills(s: Services) -> SkillsService:
        return SkillsService(
            s.registry, store.skills, approvals(s), RemindersService(store.skills, s.encryptor)
        )

    def assistant(s: Services, user: AuthUser) -> AssistantService:
        b = budget(s)
        usage = TurnUsageRecorder(b)
        return AssistantService(
            repo=store.assistant,
            users=users(s),
            budget=b,
            privacy=PrivacyService(store.privacy),
            skills=skills(s),
            llm=LLMService(s.llm, usage, user_id=user.id),
            usage=usage,
            settings=s.settings,
        )

    from fastapi import Depends

    S = Depends(get_services)
    U = Depends(get_current_user)

    def o_users(s: Services = S) -> UsersService:
        return users(s)

    def o_budget(s: Services = S) -> BudgetService:
        return budget(s)

    def o_privacy() -> PrivacyService:
        return PrivacyService(store.privacy)

    def o_memory(s: Services = S, u: AuthUser = U) -> MemoryService:
        return MemoryService(store.memory, s.encryptor, LLMService(s.llm, budget(s), user_id=u.id))

    def o_approvals(s: Services = S) -> ApprovalService:
        return approvals(s)

    def o_reminders(s: Services = S) -> RemindersService:
        return RemindersService(store.skills, s.encryptor)

    def o_skills(s: Services = S) -> SkillsService:
        return skills(s)

    def o_demo() -> DemoService:
        return DemoService(store.approvals, store.skills)

    def o_assistant(s: Services = S, u: AuthUser = U) -> AssistantService:
        return assistant(s, u)

    def o_factory(s: Services = S) -> deps.AssistantFactory:
        @asynccontextmanager
        async def factory(user: AuthUser) -> AsyncIterator[AssistantService]:
            yield assistant(s, user)

        return factory

    app.dependency_overrides.update(
        {
            deps.get_users_service: o_users,
            deps.get_budget_service: o_budget,
            deps.get_privacy_service: o_privacy,
            deps.get_memory_service: o_memory,
            deps.get_approval_service: o_approvals,
            deps.get_reminders_service: o_reminders,
            deps.get_skills_service: o_skills,
            deps.get_demo_service: o_demo,
            deps.get_assistant_service: o_assistant,
            deps.get_assistant_factory: o_factory,
        }
    )


@pytest.fixture
def app(settings: Settings, store: Store, backend: MockBackend) -> FastAPI:
    services = build_services(settings, backend=backend)
    services.db = FakeDB()  # type: ignore[assignment]
    application = create_app(services=services)
    install_fakes(application, store)
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id)}"}
