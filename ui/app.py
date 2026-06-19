"""
Streamlit chat UI for the Contact Center multiagent platform.
Run:  streamlit run ui/app.py
"""
import streamlit as st
from agents.router_agent import classify_intent
from agents.mortgage_agent import answer_mortgage_query
from agents.customer_service_agent import answer_incident_query
from config.settings import INTENT_MORTGAGE, INTENT_INCIDENT

st.set_page_config(page_title="Contact Center IA", page_icon="🏦", layout="centered")
st.title("🏦 Contact Center Bancario — IA Multiagente")
st.caption("Plataforma inteligente para hipotecas e incidencias")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("¿En qué puedo ayudarte?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando tu consulta..."):
            intent = classify_intent(prompt)
            st.caption(f"_Intención detectada: **{intent}**_")

            if intent == INTENT_MORTGAGE:
                response = answer_mortgage_query(prompt)
            elif intent == INTENT_INCIDENT:
                response = answer_incident_query(prompt)
            else:
                response = (
                    "Lo siento, no he podido identificar el motivo de tu consulta. "
                    "Por favor, contacta con nosotros al **900 000 000** o visita tu oficina más cercana."
                )

        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
