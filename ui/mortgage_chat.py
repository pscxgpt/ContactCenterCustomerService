"""
Mortgage advisor chat — multi-turn Streamlit UI for the conversational mortgage
agent. The agent gathers data across turns and runs the deterministic engine.

Run:  streamlit run ui/mortgage_chat.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import truststore
truststore.inject_into_ssl()

import streamlit as st
from agents.mortgage_agent import answer_mortgage_query

st.set_page_config(page_title="Asesor de Hipotecas", page_icon="🏦", layout="centered")
st.title("🏦 Asesor de Hipotecas")
st.caption("Simulación orientativa. Los cálculos y la decisión de riesgo son deterministas (no los hace el LLM).")

if "mortgage_msgs" not in st.session_state:
    st.session_state.mortgage_msgs = []

with st.sidebar:
    st.header("Conversación")
    if st.button("Reiniciar", use_container_width=True):
        st.session_state.mortgage_msgs = []
        st.rerun()
    st.caption(
        "Ejemplo: _\"Quiero una hipoteca fija de 200.000 € para una vivienda de "
        "250.000 €, a 30 años. Gano 3.000 € netos, soy funcionario con 8 años de "
        "antigüedad y no tengo deudas.\"_"
    )

for msg in st.session_state.mortgage_msgs:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def _history_text() -> str:
    role = {"user": "Cliente", "assistant": "Agente"}
    return "\n".join(f"{role[m['role']]}: {m['content']}" for m in st.session_state.mortgage_msgs)


if prompt := st.chat_input("Escribe tu consulta sobre hipotecas..."):
    st.session_state.mortgage_msgs.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            reply = answer_mortgage_query(_history_text())
        st.markdown(reply)

    st.session_state.mortgage_msgs.append({"role": "assistant", "content": reply})
