"""
Tests for the incident agent's deterministic handoff gate. The escalation path
short-circuits before any LLM call, so these stay offline like the rest of the
suite (they use the local FAISS store + embeddings, no Groq).
"""
from agents.customer_service_agent import answer_incident_query, HUMAN_HANDOFF_MSG
from tools.rag_search import retrieve
from config.settings import RAG_MIN_RELEVANCE


def test_offtopic_escalates_to_human_without_llm():
    # Nothing relevant in the KB → deterministic handoff, no improvised answer.
    reply = answer_incident_query("¿Qué tiempo hará mañana en Barcelona?")
    assert reply == HUMAN_HANDOFF_MSG


def test_unrelated_chitchat_escalates():
    reply = answer_incident_query("Recomiéndame un restaurante italiano")
    assert reply == HUMAN_HANDOFF_MSG


def test_ontopic_incident_passes_the_gate():
    hits = retrieve("Me han robado la tarjeta de crédito")
    assert hits, "expected at least one KB hit"
    assert hits[0].score >= RAG_MIN_RELEVANCE


def test_offtopic_scores_below_gate():
    hits = retrieve("¿Cuál es tu color favorito?")
    top = hits[0].score if hits else 0.0
    assert top < RAG_MIN_RELEVANCE
