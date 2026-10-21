"""No public endpoints in API contract v0.1 (voice turns use POST /assistant/turns with
inputMode=voice after browser STT). Kept so a server STT/TTS route can be added without
touching main.py wiring."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["voice"])
