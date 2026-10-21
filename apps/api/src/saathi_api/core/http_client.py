"""One pooled httpx.AsyncClient per process (LLM SDK + readiness probes)."""

from __future__ import annotations

import httpx

from saathi_api.core.config import Settings


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.llm_timeout_s, connect=settings.llm_connect_timeout_s),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=30),
        headers={"User-Agent": f"{settings.app_name}/0.1"},
        follow_redirects=False,
    )
