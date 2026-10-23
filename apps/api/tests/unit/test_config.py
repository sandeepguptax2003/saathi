from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_valid_settings_and_url_normalization() -> None:
    s = make_settings(cors_origins="http://a.test, https://b.test/")
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert s.cors_origins == ["http://a.test", "https://b.test"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"encryption_pepper": "short"},
        {"supabase_jwt_secret": "short"},
        {"database_url": "mysql://x"},
        {"llm_mock": False},  # no NEBIUS_API_KEY
        {"llm_mock": False, "nebius_api_key": "  "},  # blank counts as missing
        {"env": "production", "llm_mock": True},
        {"env": "production", "llm_mock": False, "nebius_api_key": "k", "cors_origins": ["*"]},
        {"daily_budget_usd": 5, "global_daily_budget_usd": 2},
    ],
)
def test_unsafe_settings_refuse_to_boot(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        make_settings(**overrides)


def test_database_password_fills_supabase_placeholder() -> None:
    s = make_settings(
        database_url="postgresql://postgres.ref:[YOUR-PASSWORD]@pooler.test:6543/postgres",
        database_password="p@ss/word",
    )
    assert (
        s.database_url
        == "postgresql+asyncpg://postgres.ref:p%40ss%2Fword@pooler.test:6543/postgres"
    )


def test_database_placeholder_without_password_refuses_to_boot() -> None:
    with pytest.raises(ValidationError):
        make_settings(database_url="postgresql://u:[YOUR-PASSWORD]@h:5432/db")
