"""Typed, validated configuration. The app refuses to boot on missing or unsafe values."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "test", "preview", "production"]


class ModelPrice:
    """USD per 1M tokens (input, output)."""

    __slots__ = ("input_per_m", "output_per_m")

    def __init__(self, input_per_m: float, output_per_m: float) -> None:
        self.input_per_m = input_per_m
        self.output_per_m = output_per_m


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- runtime
    env: Environment = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_name: str = "saathi-api"
    release: str | None = Field(default=None, description="git SHA, used for Sentry releases")

    # --- LLM (Nebius Token Factory, OpenAI compatible)
    nebius_api_key: SecretStr | None = None
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    model_fast: str = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    model_reasoning: str = "nvidia/nemotron-3-super-120b-a12b"
    model_ultra: str | None = None
    model_embed: str = "Qwen/Qwen3-Embedding-8B"
    embed_dims: int = 1024
    llm_mock: bool = False
    llm_timeout_s: float = Field(default=20.0, gt=0, le=120)
    llm_connect_timeout_s: float = Field(default=5.0, gt=0, le=30)
    llm_max_retries: int = Field(default=3, ge=1, le=6)
    llm_retry_base_delay_s: float = Field(default=0.5, ge=0)
    llm_max_tokens: int = Field(default=512, ge=16, le=8192)
    llm_router_confidence_min: float = Field(default=0.6, ge=0, le=1)
    circuit_failure_threshold: int = Field(default=5, ge=1)
    circuit_reset_s: float = Field(default=30.0, gt=0)

    # Prices USD per 1M tokens, from tokenfactory.nebius.com/api/public/models_info (2026-10-21).
    price_fast_in: float = 0.06
    price_fast_out: float = 0.24
    price_reasoning_in: float = 0.30
    price_reasoning_out: float = 0.90
    price_ultra_in: float = 1.00
    price_ultra_out: float = 3.00
    price_embed_in: float = 0.01

    # --- database
    database_url: str
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_pgbouncer: bool = Field(
        default=False, description="Supabase pooler (transaction mode): disable stmt cache"
    )
    db_enforce_rls: bool = Field(
        default=False, description="SET LOCAL ROLE authenticated + jwt claims per request"
    )

    # --- auth: Supabase project JWT secret
    supabase_url: str
    supabase_jwt_secret: SecretStr
    supabase_jwt_audience: str = "authenticated"

    # --- encryption
    encryption_pepper: SecretStr
    encryption_key_version: int = Field(default=1, ge=1, le=65535)
    encryption_legacy_peppers: dict[int, SecretStr] = Field(
        default_factory=dict, description='JSON, e.g. {"1": "..."} for rotated-out versions'
    )

    # --- budget
    daily_budget_usd: float = Field(default=1.0, gt=0)
    global_daily_budget_usd: float = Field(default=2.0, gt=0)
    budget_alert_ratio: float = Field(default=0.7, gt=0, le=1)
    budget_timezone: str = "Asia/Kolkata"

    # --- HTTP
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    rate_limit_turns_per_min: int = Field(default=30, ge=1)
    rate_limit_default_per_min: int = Field(default=120, ge=1)
    approval_ttl_minutes: int = Field(default=30, ge=1)
    idempotency_replay_hours: int = Field(default=24, ge=1)

    # --- observability
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0, le=1)

    @field_validator("nebius_api_key", "sentry_dsn", "model_ultra", "release", mode="before")
    @classmethod
    def _blank_is_none(cls, v: object) -> object:
        """`KEY=` in .env means unset, not an empty secret."""
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        return v

    @field_validator("database_url")
    @classmethod
    def _asyncpg_url(cls, v: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix) :]
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must be a postgres URL")
        return v

    @field_validator("encryption_pepper")
    @classmethod
    def _pepper_strength(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("ENCRYPTION_PEPPER must be at least 32 characters")
        return v

    @field_validator("supabase_jwt_secret")
    @classmethod
    def _jwt_secret_strength(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("SUPABASE_JWT_SECRET must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def _env_rules(self) -> Settings:
        if not self.llm_mock and self.nebius_api_key is None:
            raise ValueError("NEBIUS_API_KEY is required unless LLM_MOCK=true")
        if self.env == "production":
            if self.llm_mock:
                raise ValueError("LLM_MOCK must be false in production")
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS must be an explicit allowlist in production")
        if self.global_daily_budget_usd < self.daily_budget_usd:
            raise ValueError("GLOBAL_DAILY_BUDGET_USD must be >= DAILY_BUDGET_USD")
        if self.encryption_key_version in self.encryption_legacy_peppers:
            raise ValueError("current ENCRYPTION_KEY_VERSION must not appear in legacy peppers")
        return self

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def peppers(self) -> dict[int, bytes]:
        keys = {k: v.get_secret_value().encode() for k, v in self.encryption_legacy_peppers.items()}
        keys[self.encryption_key_version] = self.encryption_pepper.get_secret_value().encode()
        return keys

    def price_table(self) -> dict[str, ModelPrice]:
        table = {
            self.model_fast: ModelPrice(self.price_fast_in, self.price_fast_out),
            self.model_reasoning: ModelPrice(self.price_reasoning_in, self.price_reasoning_out),
            self.model_embed: ModelPrice(self.price_embed_in, 0.0),
        }
        if self.model_ultra:
            table[self.model_ultra] = ModelPrice(self.price_ultra_in, self.price_ultra_out)
        return table


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # values come from the environment
