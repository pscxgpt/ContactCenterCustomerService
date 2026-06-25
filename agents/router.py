"""
Tiered router (cascade) — the scalable routing approach, demo-sized.

Tier 0  Deterministic guards   keyword shortcuts + explicit human request   (no model)
Tier 1  Semantic classifier    cosine similarity vs intent exemplars         (local embeddings)
Tier 2  LLM fallback           constrained classification, only when unsure  (Groq for demo)

Escalation is gated by confidence: most turns resolve at Tier 0/1 (cheap, local,
private); only genuinely ambiguous ones reach the LLM. `route_turn` adds sticky
sessions so a multi-turn flow (e.g. a mortgage simulation) isn't re-routed on
every follow-up.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np

from config import settings as S
from config.intents import INTENTS, HUMAN_PHRASES, normalize
from tools.embeddings import get_embeddings

# route_to sentinels (besides the intent names themselves)
ROUTE_HUMAN = "humano"
ROUTE_CLARIFY = "clarify"
ROUTE_UNKNOWN = S.INTENT_UNKNOWN

_HUMAN_PHRASES_NORM = [normalize(p) for p in HUMAN_PHRASES]


@dataclass
class RouteDecision:
    route_to: str               # intent name | ROUTE_HUMAN | ROUTE_CLARIFY | ROUTE_UNKNOWN
    tier: int                   # 0, 1 or 2 (which layer decided)
    confidence: float           # 0..1
    intent: Optional[str] = None  # best-guess intent (even when clarifying)
    reason: str = ""

    @property
    def chip(self) -> str:
        """Short label for the demo UI, e.g. 'Tier 1 · hipotecas · 0.82'."""
        return f"Tier {self.tier} · {self.route_to} · {self.confidence:.2f}"


class Router:
    def __init__(self):
        self.intent_names = list(INTENTS.keys())
        exemplars, labels = [], []
        for name, cfg in INTENTS.items():
            for ex in cfg["exemplars"]:
                exemplars.append(ex)
                labels.append(name)
        # embeddings are L2-normalized → dot product == cosine similarity
        self._matrix = np.asarray(get_embeddings().embed_documents(exemplars), dtype=np.float32)
        self._labels = labels

    # ── Tier 1 helper ──
    def _semantic_scores(self, message: str) -> dict[str, float]:
        q = np.asarray(get_embeddings().embed_query(message), dtype=np.float32)
        sims = self._matrix @ q
        return {
            name: float(max(sims[i] for i, lbl in enumerate(self._labels) if lbl == name))
            for name in self.intent_names
        }

    def classify(self, message: str, use_llm: bool = True) -> RouteDecision:
        text = normalize(message)

        # ── Tier 0: explicit human request ──
        if any(p in text for p in _HUMAN_PHRASES_NORM):
            return RouteDecision(ROUTE_HUMAN, 0, 1.0, reason="solicitud explícita de gestor")

        # ── Tier 0: high-precision keyword shortcut (only if unambiguous) ──
        hits = {
            name for name, cfg in INTENTS.items()
            if any(normalize(kw) in text for kw in cfg["keywords"])
        }
        if len(hits) == 1:
            name = next(iter(hits))
            return RouteDecision(name, 0, 0.9, intent=name, reason="palabra clave")

        # ── Tier 1: semantic classifier ──
        scores = self._semantic_scores(message)
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_name, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        if best_score >= S.ROUTER_TIER1_HIGH and (best_score - second_score) >= S.ROUTER_TIER1_MARGIN:
            return RouteDecision(best_name, 1, round(best_score, 3), intent=best_name, reason="semántico")

        # ── Tier 2: LLM fallback (only when Tier 1 wasn't confident) ──
        if use_llm:
            from agents.router_agent import classify_intent
            llm_intent = classify_intent(message)
            if llm_intent in self.intent_names:
                return RouteDecision(llm_intent, 2, max(round(best_score, 3), 0.70),
                                     intent=llm_intent, reason="LLM")

        # ── Fallback: clarify if plausibly in-scope, else out-of-scope ──
        if best_score >= S.ROUTER_TIER1_LOW:
            return RouteDecision(ROUTE_CLARIFY, 1, round(best_score, 3),
                                 intent=best_name, reason="ambiguo")
        return RouteDecision(ROUTE_UNKNOWN, 1, round(best_score, 3), reason="fuera de alcance")


@lru_cache(maxsize=1)
def get_router() -> Router:
    return Router()


def route_turn(message: str, session: dict, use_llm: bool = True) -> RouteDecision:
    """
    Stateful routing for a conversation. `session` is a mutable dict holding
    `active_intent`. Keeps the caller with the active specialist unless the
    customer clearly switches topic or asks for a human.
    """
    decision = get_router().classify(message, use_llm=use_llm)

    if decision.route_to == ROUTE_HUMAN:
        session["active_intent"] = None
        return decision

    active = session.get("active_intent")
    if active in INTENTS:
        switching = (
            decision.route_to in INTENTS
            and decision.route_to != active
            and decision.confidence >= S.ROUTER_STICKY_SWITCH_CONF
        )
        if not switching:
            # stay with the active specialist (continuation of the flow)
            return RouteDecision(active, decision.tier, decision.confidence,
                                 intent=active, reason="continuación")

    if decision.route_to in INTENTS:
        session["active_intent"] = decision.route_to
    return decision
