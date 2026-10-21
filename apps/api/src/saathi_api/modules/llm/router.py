"""No public endpoints: the LLM is only reached through the assistant turn flow.

Readiness (Token Factory reachability) is reported by GET /ready.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["llm"])
