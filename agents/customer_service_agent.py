"""
Customer service agent — handles incidents/complaints via RAG over the bank's
knowledge base.

Design (same "Mind + Tools" split as the mortgage agent): retrieval and the
escalation decision are **deterministic Python**, the LLM only composes the
Spanish reply from the retrieved context. Concretely:

  1. retrieve() the top KB hits with cosine relevance scores.
  2. If the best hit is below RAG_MIN_RELEVANCE → escalate to a human verbatim
     (no LLM call), so we never improvise an answer the KB can't support.
  3. Otherwise the LLM answers **only** from the provided context, keeping the
     conversation history in mind; if the context doesn't actually cover the
     question it says so and offers a human, instead of inventing.
"""
from crewai import Agent, Task, Crew

from tools.rag_search import retrieve
from config.llm_patches import patch_groq_cache
from config.settings import CUSTOMER_SERVICE_MODEL, RETRIEVAL_K, RAG_MIN_RELEVANCE

# Groq rejects CrewAI's cache_breakpoint field; apply at import so this agent
# works standalone, not only when the router happens to be imported first.
patch_groq_cache()

HUMAN_HANDOFF_MSG = (
    "Lo siento, no encuentro información fiable sobre esto en nuestra base de "
    "conocimiento. Te paso con un gestor humano que podrá ayudarte mejor. "
    "Un momento, por favor."
)

_BACKSTORY = """
Eres un agente de atención al cliente de un banco español. Ayudas con
incidencias y reclamaciones: tarjetas, transferencias, fraude, comisiones y
cuentas. Respondes siempre en español, con tono claro y resolutivo.
""".strip()


def _format_context(hits) -> str:
    return "\n\n".join(
        f"[{i}] (relevancia={h.score:.2f})\nP: {h.query}\nR: {h.response}"
        for i, h in enumerate(hits, 1)
    )


def answer_incident_query(user_message: str, conversation_history: str = "") -> str:
    """Resolve an incident, grounded in the KB, with a deterministic handoff gate.

    `conversation_history` is the prior transcript (optional) so multi-turn
    incident conversations keep context.
    """
    hits = retrieve(user_message, k=RETRIEVAL_K)
    top_score = hits[0].score if hits else 0.0

    # Deterministic gate: nothing relevant enough → escalate, don't improvise.
    if not hits or top_score < RAG_MIN_RELEVANCE:
        return HUMAN_HANDOFF_MSG

    context = _format_context(hits)
    history_block = (
        f"Historial de la conversación:\n{conversation_history}\n\n"
        if conversation_history.strip() else ""
    )

    description = f"""{history_block}Consulta actual del cliente:
"{user_message}"

Información recuperada de la base de conocimiento (úsala como única fuente):
{context}

Instrucciones:
- Responde en español, de forma breve y útil, resolviendo la incidencia.
- Básate ÚNICAMENTE en la información recuperada. No inventes datos, cifras,
  plazos ni procedimientos que no aparezcan arriba.
- Si la información recuperada no cubre realmente la consulta, dilo con
  honestidad y ofrece pasar al cliente con un gestor humano.
- Ten en cuenta el historial para no repetir preguntas ya respondidas."""

    agent = Agent(
        role="Customer Service Agent",
        goal="Resolver incidencias del cliente usando solo la base de conocimiento.",
        backstory=_BACKSTORY,
        llm=CUSTOMER_SERVICE_MODEL,
        verbose=False,
    )
    task = Task(
        description=description,
        agent=agent,
        expected_output="Una respuesta en español, fundamentada en el contexto, que resuelve o escala la incidencia.",
    )
    result = Crew(agents=[agent], tasks=[task], verbose=False).kickoff()
    return str(result)
