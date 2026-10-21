from __future__ import annotations

from typing import Literal

from saathi_api.core.schemas import CamelModel

VoiceEngine = Literal["browser", "faster-whisper", "voxcpm2"]


class Transcript(CamelModel):
    text: str
    locale: str
    confidence: float | None = None


class SynthesizedAudio(CamelModel):
    content_type: str
    audio_b64: str
    voice: str
