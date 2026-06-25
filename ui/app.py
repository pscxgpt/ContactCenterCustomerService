"""
Unified Streamlit chat for the Contact Center multiagent platform.

The tiered router decides who handles each turn (with sticky sessions); the
mortgage flow is multi-turn. Each turn can come in by **text** or by **voice**
(🎙️ record → Groq Whisper → router → agent → edge-tts → 🔊), and the spoken
reply is optional via the sidebar toggle.

Run:  streamlit run ui/app.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import truststore
truststore.inject_into_ssl()

import streamlit as st
from agents.router import route_turn, ROUTE_HUMAN, ROUTE_CLARIFY
from agents.mortgage_agent import answer_mortgage_query
from agents.customer_service_agent import answer_incident_query
from config.settings import INTENT_MORTGAGE, INTENT_INCIDENT
from tools.voice import transcribe, synthesize

st.set_page_config(page_title="Contact Center IA", page_icon="🏦", layout="centered")
st.title("🏦 Contact Center Bancario — IA Multiagente")
st.caption("Enrutador por niveles (Tier 0 reglas · Tier 1 semántico · Tier 2 LLM) con sesión persistente.")

with st.sidebar:
    st.header("🎙️ Voz")
    speak_replies = st.toggle("Leer las respuestas en voz alta", value=True)
    st.caption("STT: Groq Whisper · TTS: edge-tts")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "router_session" not in st.session_state:
    st.session_state.router_session = {"active_intent": None}
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None


def _transcript(messages) -> str:
    role = {"user": "Cliente", "assistant": "Agente"}
    return "\n".join(f"{role[m['role']]}: {m['content']}" for m in messages)


def _generate(prompt: str) -> tuple[str, str]:
    """Route the turn and produce the agent reply. Returns (chip, response)."""
    decision = route_turn(prompt, st.session_state.router_session)
    chip = f"🧭 {decision.chip} · {decision.reason}"

    if decision.route_to == INTENT_MORTGAGE:
        # Mortgage agent reads the latest client turn from the full transcript.
        response = answer_mortgage_query(_transcript(st.session_state.messages))
    elif decision.route_to == INTENT_INCIDENT:
        # Pass prior turns as context; the current message is the query.
        response = answer_incident_query(prompt, _transcript(st.session_state.messages[:-1]))
    elif decision.route_to == ROUTE_HUMAN:
        response = ("Te paso con un gestor humano que continuará atendiéndote. "
                    "Un momento, por favor.")
    elif decision.route_to == ROUTE_CLARIFY:
        response = ("Para ayudarte mejor, ¿tu consulta es sobre una **hipoteca** o sobre "
                    "una **incidencia** de tu cuenta (tarjeta, transferencia, fraude...)?")
    else:
        response = ("Lo siento, no he identificado el motivo. Puedo ayudarte con "
                    "**hipotecas** o **incidencias**. ¿Cuál es tu consulta?")
    return chip, response


def handle_turn(prompt: str) -> None:
    """Append the user turn, generate the reply (+ optional TTS), and render both."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando tu consulta..."):
            chip, response = _generate(prompt)
            audio = None
            if speak_replies:
                # Strip markdown emphasis so the voice doesn't read asterisks/backticks.
                clean = response.replace("*", "").replace("`", "")
                try:
                    audio = synthesize(clean)
                except Exception as exc:  # degrade to text, never crash the demo
                    st.warning(f"No se pudo generar el audio: {exc}")
        st.caption(chip)
        st.markdown(response)
        if audio:
            st.audio(audio, format="audio/mp3", autoplay=True)

    st.session_state.messages.append(
        {"role": "assistant", "content": response, "chip": chip, "audio": audio}
    )


# ── Render history ───────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("chip"):
            st.caption(msg["chip"])
        st.markdown(msg["content"])
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/mp3")  # no autoplay for past turns

# ── Voice input ────────────────────────────────────────────────────────────────
audio_in = st.audio_input("🎙️ Habla con el asistente (o escribe abajo)")
if audio_in is not None:
    audio_id = getattr(audio_in, "file_id", None) or hash(audio_in.getvalue())
    if audio_id != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_id
        with st.spinner("Transcribiendo..."):
            try:
                spoken = transcribe(audio_in.getvalue(), filename="speech.wav")
            except Exception as exc:
                spoken = ""
                st.warning(f"No se pudo transcribir el audio: {exc}")
        if spoken:
            handle_turn(spoken)
        else:
            st.info("No te he entendido. ¿Puedes repetirlo?")

# ── Text input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("¿En qué puedo ayudarte?"):
    handle_turn(prompt)
