"""
Unified Streamlit chat for the Contact Center multiagent platform.
The tiered router decides who handles each turn (with sticky sessions); the
mortgage flow is multi-turn.

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

st.set_page_config(page_title="Contact Center IA", page_icon="🏦", layout="centered")
st.title("🏦 Contact Center Bancario — IA Multiagente")
st.caption("Enrutador por niveles (Tier 0 reglas · Tier 1 semántico · Tier 2 LLM) con sesión persistente.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "router_session" not in st.session_state:
    st.session_state.router_session = {"active_intent": None}

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def _mortgage_history() -> str:
    role = {"user": "Cliente", "assistant": "Agente"}
    return "\n".join(f"{role[m['role']]}: {m['content']}" for m in st.session_state.messages)


if prompt := st.chat_input("¿En qué puedo ayudarte?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando tu consulta..."):
            decision = route_turn(prompt, st.session_state.router_session)
            st.caption(f"🧭 {decision.chip} · _{decision.reason}_")

            if decision.route_to == INTENT_MORTGAGE:
                response = answer_mortgage_query(_mortgage_history())
            elif decision.route_to == INTENT_INCIDENT:
                response = answer_incident_query(prompt)
            elif decision.route_to == ROUTE_HUMAN:
                response = ("Te paso con un gestor humano que continuará atendiéndote. "
                            "Un momento, por favor.")
            elif decision.route_to == ROUTE_CLARIFY:
                response = ("Para ayudarte mejor, ¿tu consulta es sobre una **hipoteca** o sobre "
                            "una **incidencia** de tu cuenta (tarjeta, transferencia, fraude...)?")
            else:
                response = ("Lo siento, no he identificado el motivo. Puedo ayudarte con "
                            "**hipotecas** o **incidencias**. ¿Cuál es tu consulta?")

        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
