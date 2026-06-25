"""Tests for the tiered router (offline: Tier 0/1 only, use_llm=False)."""
from agents.router import get_router, route_turn, ROUTE_HUMAN
from config.settings import INTENT_MORTGAGE, INTENT_INCIDENT


def test_tier0_keyword_mortgage():
    d = get_router().classify("Quiero una hipoteca para comprar un piso", use_llm=False)
    assert d.route_to == INTENT_MORTGAGE and d.tier == 0


def test_tier0_keyword_incident():
    d = get_router().classify("Me han robado la tarjeta", use_llm=False)
    assert d.route_to == INTENT_INCIDENT and d.tier == 0


def test_tier0_human_request():
    d = get_router().classify("Prefiero hablar con una persona, por favor", use_llm=False)
    assert d.route_to == ROUTE_HUMAN and d.tier == 0


def test_tier1_semantic_without_keyword():
    # No registered keyword here → must be resolved by the semantic tier.
    d = get_router().classify("Necesito financiación para adquirir mi primera casa", use_llm=False)
    assert d.route_to == INTENT_MORTGAGE and d.tier == 1


def test_out_of_scope_is_not_forced():
    d = get_router().classify("¿Qué tiempo hará mañana en Barcelona?", use_llm=False)
    assert d.route_to in ("desconocido", "clarify")


def test_sticky_session_keeps_active_agent():
    session = {"active_intent": None}
    first = route_turn("Quiero simular una hipoteca", session, use_llm=False)
    assert first.route_to == INTENT_MORTGAGE
    # A bare follow-up with no clear intent should stay with mortgages.
    follow = route_turn("¿y a 25 años?", session, use_llm=False)
    assert follow.route_to == INTENT_MORTGAGE


def test_explicit_human_breaks_stickiness():
    session = {"active_intent": INTENT_MORTGAGE}
    d = route_turn("quiero hablar con una persona", session, use_llm=False)
    assert d.route_to == ROUTE_HUMAN and session["active_intent"] is None
