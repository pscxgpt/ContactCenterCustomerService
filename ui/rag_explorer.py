"""
RAG Explorer — a focused Streamlit UI to verify the FAQ vector search works.

This screen does NOT call any LLM/agent. It exercises only the FAISS retrieval
so you can type a question and inspect the matching Q&A pairs and their scores.

Run:  streamlit run ui/rag_explorer.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import truststore
truststore.inject_into_ssl()

import streamlit as st
from tools.rag_search import _load_store
from config.settings import VECTOR_STORE_PATH, EMBEDDING_MODEL, RETRIEVAL_K

st.set_page_config(page_title="RAG Explorer", page_icon="🔎", layout="centered")
st.title("🔎 RAG Explorer — Banking FAQ")
st.caption("Verificación de la búsqueda semántica sobre la base de conocimiento (sin LLM).")


@st.cache_resource(show_spinner="Cargando índice FAISS y modelo de embeddings...")
def load_store():
    return _load_store()


if not os.path.exists(VECTOR_STORE_PATH):
    st.error(
        "No se encontró el índice vectorial. Ejecuta primero:\n\n"
        "`.venv\\Scripts\\python.exe scripts\\build_index.py`"
    )
    st.stop()

store = load_store()
num_vectors = store.index.ntotal

with st.sidebar:
    st.header("Ajustes")
    k = st.slider("Resultados a recuperar (k)", min_value=1, max_value=10, value=RETRIEVAL_K)
    min_rel = st.slider("Relevancia mínima", min_value=0.0, max_value=1.0, value=0.0, step=0.05)
    st.divider()
    st.metric("Vectores en el índice", num_vectors)
    st.caption(f"Modelo: `{EMBEDDING_MODEL}`")

query = st.text_input(
    "Escribe una consulta de cliente",
    placeholder="p. ej. I lost my debit card, what should I do?",
)

examples = [
    "How do I open an account?",
    "I lost my debit card",
    "transfer money to another account",
    "forgot my online banking password",
]
cols = st.columns(len(examples))
for col, ex in zip(cols, examples):
    if col.button(ex, use_container_width=True):
        query = ex

if query:
    results = store.similarity_search_with_relevance_scores(query, k=k)
    results = [(d, s) for d, s in results if s >= min_rel]

    if not results:
        st.warning("No hay resultados por encima del umbral de relevancia.")
    else:
        st.subheader(f"{len(results)} resultado(s) para: _{query}_")
        for i, (doc, score) in enumerate(results, 1):
            q = doc.metadata.get("query", "")
            a = doc.metadata.get("response", doc.page_content)
            with st.container(border=True):
                top = st.columns([0.8, 0.2])
                top[0].markdown(f"**{i}. {q}**")
                top[1].metric("relevancia", f"{score:.2f}")
                st.progress(max(0.0, min(1.0, float(score))))
                st.markdown(a)
