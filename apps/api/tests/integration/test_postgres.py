"""Runs against a real Postgres + pgvector (CI service container / docker-compose).

Set TEST_DATABASE_URL (e.g. postgresql://saathi:saathi@localhost:5432/saathi_test) to enable.
Applies migrations, exercises the SQL repositories, then downgrades.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from saathi_api.core.crypto import Encryptor
from saathi_api.core.db import Database
from saathi_api.modules.approvals.repository import SqlApprovalsRepository
from saathi_api.modules.approvals.service import ApprovalService
from saathi_api.modules.memory.models import Memory
from saathi_api.modules.memory.repository import SqlMemoryRepository
from saathi_api.modules.skills.service import SimulatedExecutor
from saathi_api.modules.users.repository import SqlUsersRepository
from tests.conftest import make_settings

DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set (no Postgres available)"),
]
API_ROOT = Path(__file__).resolve().parents[2]


def _alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": DB_URL or ""}
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=API_ROOT, env=env, check=True)  # noqa: S603


@pytest.fixture(scope="module")
def migrated() -> object:
    _alembic("upgrade", "head")
    yield None
    _alembic("downgrade", "base")


@pytest.fixture
async def db(migrated: object) -> AsyncIterator[Database]:
    database = Database(make_settings(database_url=DB_URL))
    yield database
    await database.dispose()


async def test_ping_and_user_upsert(db: Database) -> None:
    assert await db.ping()
    uid = uuid.uuid4()
    async with db.session(user_id=uid) as s:
        repo = SqlUsersRepository(s)
        u1 = await repo.create_if_missing(uid, is_demo=True)
        u2 = await repo.create_if_missing(uid, is_demo=False)
        await repo.commit()
        assert u1.id == u2.id and u2.is_demo is True


async def test_vector_search_and_approval_idempotency(db: Database) -> None:
    uid = uuid.uuid4()
    enc = Encryptor({1: b"z" * 40}, 1)
    async with db.session(user_id=uid) as s:
        await SqlUsersRepository(s).create_if_missing(uid, is_demo=True)
        mem = SqlMemoryRepository(s)
        vec = [0.0] * 1024
        vec[0] = 1.0
        blob = enc.encrypt(uid, "fact", purpose="memory")
        await mem.add(
            Memory(
                user_id=uid,
                kind="fact",
                content_ciphertext=blob.ciphertext,
                nonce=blob.nonce,
                key_version=1,
                embedding=vec,
                source="user",
            )
        )
        hits = await mem.search(uid, vec, None, 5)
        assert hits and hits[0][1] == pytest.approx(1.0)

        svc = ApprovalService(SqlApprovalsRepository(s), enc, SimulatedExecutor())
        action = await svc.create(
            uid,
            skill="bills",
            action_type="bill_payment",
            payload={"amountInr": 1},
            summary="Pay ₹1",
        )
        first = await svc.decide(uid, action.id, "approve", f"it-{uuid.uuid4().hex}")
        assert first.action.status == "executed"
