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
     question it transfers to a human instead of inventing.

Style: this is a phone line, so replies are short and direct (call-style). The
agent IS the customer-service line, so it never tells the caller to "phone
customer service / a number" — it transfers to a human colleague instead.
"""
from crewai import Agent, Task, Crew

from tools.rag_search import retrieve
from config.llm_patches import patch_groq_cache
from config.settings import CUSTOMER_SERVICE_MODEL, RETRIEVAL_K, RAG_MIN_RELEVANCE

# Groq rejects CrewAI's cache_breakpoint field; apply at import so this agent
# works standalone, not only when the router happens to be imported first.
patch_groq_cache()

HUMAN_HANDOFF_MSG = (
    "Para esto te paso con un gestor que te lo resolverá enseguida. "
    "Un momento, por favor."
)

_BACKSTORY = """
Eres un agente telefónico de atención al cliente de un banco español. Esta
conversación ES la línea de atención al cliente: el cliente ya está hablando
contigo, así que NUNCA le digas que llame a atención al cliente, a un número
de teléfono ni a una línea de ayuda. Si no puedes resolver algo, le pasas con
un gestor humano (un compañero), nunca con un número.

Hablas como en una llamada: frases cortas, directas y cercanas. Vas al grano,
sin listas largas, sin enumerar lo que sabes o no sabes, y sin despedidas
largas.
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

Instrucciones (estilo llamada telefónica):
- Responde en español, MUY breve y directo: 1-2 frases, 3 como máximo.
- Básate ÚNICAMENTE en la información recuperada. No inventes datos, cifras,
  plazos ni procedimientos que no aparezcan arriba.
- NUNCA digas al cliente que llame a atención al cliente, a un número o a una
  línea de ayuda: TÚ eres esa línea. Si la información recuperada no resuelve
  realmente su consulta, dile en una sola frase que le pasas con un gestor que
  lo resolverá (no des un número).
- No enumeres lo que sabes o no sabes, ni añadas despedidas largas.
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
        expected_output="Respuesta breve (1-3 frases), en español y estilo llamada, fundamentada en el contexto, que resuelve la incidencia o pasa al cliente con un gestor (nunca remite a llamar a un número).",
    )
    result = Crew(agents=[agent], tasks=[task], verbose=False).kickoff()
    return str(result)
