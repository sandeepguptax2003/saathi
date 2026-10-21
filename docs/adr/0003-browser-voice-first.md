# ADR 0003: Browser speech first, server voice as optional

- Status: Accepted (2026-10-20)
- Deciders: Sandeep Gupta

## Context
Saathi is voice-first in Hindi, English, and Hinglish. Good Hindi TTS (VoxCPM2) needs a GPU for real-time output, and server STT (faster-whisper) needs RAM and CPU we do not have on Render's free 512 MB / 0.1 CPU instance. The demo must stay live until Dec 15 without paid GPUs. The maintainer's laptop (GTX 1650 Ti, 4 GB) cannot be a 24/7 host.

## Decision
- **STT:** browser Web Speech API with `hi-IN` / `en-IN` (Chrome, Edge, Android) is the primary path. Text input is always available.
- **TTS:** browser `speechSynthesis` with a `hi-IN` voice, falling back to English voice plus on-screen text.
- The API stays text-in / text-out (SSE); the `voice` module keeps STT/TTS adapters behind an interface so a server engine can be plugged in later.
- **VoxCPM2** (Apache-2.0) is used offline on the laptop to pre-render the Hindi voice-over for the demo video. faster-whisper is used locally for evaluation only.

## Consequences
- ✅ Zero server cost and no GPU dependency for the live demo; lower latency (no audio upload).
- ✅ Audio never leaves the user's device for our servers.
- ⚠️ Browser STT may route audio to the browser vendor's speech service; disclosed in the UI and SECURITY.md scope notes.
- ⚠️ Firefox and some iOS versions lack Hindi recognition: the UI detects support and offers text input with a notice.
- ⚠️ Voice quality varies by device.

## Alternatives considered
- **Hosted VoxCPM2 on Hugging Face ZeroGPU**: needs a paid PRO plan; not approved.
- **faster-whisper on Render**: too slow on 0.1 CPU and risks the 512 MB memory limit.
