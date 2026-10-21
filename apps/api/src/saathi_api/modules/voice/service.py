from __future__ import annotations

from typing import Protocol

from saathi_api.modules.voice.schemas import SynthesizedAudio, Transcript, VoiceEngine


class SpeechToText(Protocol):
    engine: VoiceEngine

    async def transcribe(self, audio: bytes, *, locale: str, content_type: str) -> Transcript: ...


class TextToSpeech(Protocol):
    engine: VoiceEngine

    async def synthesize(
        self, text: str, *, locale: str, voice: str | None
    ) -> SynthesizedAudio: ...


class BrowserVoiceUnavailable(Exception):
    """Raised when a server-side voice op is requested but voice runs in the browser."""


class BrowserSTT:
    """Placeholder: STT happens client-side (Web Speech API hi-IN / en-IN)."""

    engine: VoiceEngine = "browser"

    async def transcribe(self, audio: bytes, *, locale: str, content_type: str) -> Transcript:
        raise BrowserVoiceUnavailable("STT runs in the browser in v0.1")


class BrowserTTS:
    """Placeholder: TTS happens client-side (speechSynthesis hi-IN)."""

    engine: VoiceEngine = "browser"

    async def synthesize(self, text: str, *, locale: str, voice: str | None) -> SynthesizedAudio:
        raise BrowserVoiceUnavailable("TTS runs in the browser in v0.1")


class VoiceService:
    def __init__(self, stt: SpeechToText | None = None, tts: TextToSpeech | None = None) -> None:
        self.stt: SpeechToText = stt or BrowserSTT()
        self.tts: TextToSpeech = tts or BrowserTTS()

    def capabilities(self) -> dict[str, str]:
        return {"stt": self.stt.engine, "tts": self.tts.engine}
