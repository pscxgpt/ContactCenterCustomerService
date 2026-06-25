"""
Live round-trip check for the voice layer: text → TTS (edge-tts) → STT (Groq
Whisper) → text. Confirms both cloud legs work on this machine/network before
the demo.

Run:  .venv\\Scripts\\python.exe scripts\\voice_smoke.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tools.voice import synthesize, transcribe

PHRASE = "Hola, quería información para pedir una hipoteca a treinta años."


def main() -> int:
    print(f"Texto original : {PHRASE}")

    print("→ TTS (edge-tts)…")
    audio = synthesize(PHRASE)
    print(f"  MP3 generado  : {len(audio)} bytes")
    if not audio:
        print("✗ TTS devolvió audio vacío.")
        return 1

    print("→ STT (Groq Whisper)…")
    text = transcribe(audio, filename="speech.mp3")
    print(f"  Transcripción : {text}")
    if not text:
        print("✗ STT no devolvió texto.")
        return 1

    print("\n✅ Round-trip de voz OK (TTS y STT funcionan).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
