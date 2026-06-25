"""
Voice I/O for the contact center — a thin, swappable layer around the agents.

  • transcribe(audio)  : speech → text   (Groq Whisper)
  • synthesize(text)   : text → MP3 bytes (edge-tts, neural Spanish voice)

Both are demo defaults running in the cloud, chosen to mirror the LLM decision:
fast and reliable for a live pitch, with a clean local prod swap (faster-whisper
for STT, Piper for TTS) that touches only this file — the router and agents are
unaware of how audio gets in or out.
"""
from __future__ import annotations

import asyncio

# OS cert store for SSL so Groq/edge-tts work behind corporate proxies, from any
# entry point (UI, scripts, tests) — same pattern as tools/embeddings.py.
import truststore
truststore.inject_into_ssl()

import edge_tts
from groq import Groq

from config.settings import GROQ_API_KEY, STT_MODEL, STT_LANGUAGE, TTS_VOICE

_groq_client: Groq | None = None


def _client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def transcribe(audio_bytes: bytes, filename: str = "speech.wav") -> str:
    """Speech → text via Groq Whisper. Returns the transcription (stripped)."""
    if not audio_bytes:
        return ""
    result = _client().audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=STT_MODEL,
        language=STT_LANGUAGE,
    )
    return (result.text or "").strip()


async def _synthesize_async(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    buf = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    return bytes(buf)


def synthesize(text: str, voice: str | None = None) -> bytes:
    """Text → MP3 bytes via edge-tts. Returns b'' for empty input."""
    text = (text or "").strip()
    if not text:
        return b""
    voice = voice or TTS_VOICE
    try:
        return asyncio.run(_synthesize_async(text, voice))
    except RuntimeError:
        # A loop is already running in this thread (rare under Streamlit) — run
        # the coroutine on a fresh loop instead of failing.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_synthesize_async(text, voice))
        finally:
            loop.close()
