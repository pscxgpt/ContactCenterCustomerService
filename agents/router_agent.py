"""
Router agent — classifies user intent and extracts parameters.
Returns one of: INTENT_MORTGAGE, INTENT_INCIDENT, INTENT_UNKNOWN.
"""
from crewai import Agent, Task, Crew
from config.settings import ROUTER_MODEL, INTENT_MORTGAGE, INTENT_INCIDENT, INTENT_UNKNOWN


_SYSTEM_PROMPT = """
You are a customer service router for a Spanish bank.
Your ONLY job is to classify the customer's message into one of these categories:
- hipotecas: anything about mortgages, loan conditions, interest rates, monthly payments
- incidencias: complaints, card issues, account problems, fraud, transfers
- desconocido: anything else

Reply with ONLY the category word in lowercase. No explanations.
""".strip()


def classify_intent(user_message: str) -> str:
    """Return the intent string for the given user message."""
    agent = Agent(
        role="Intent Router",
        goal="Classify the customer message into exactly one intent category.",
        backstory=_SYSTEM_PROMPT,
        llm=ROUTER_MODEL,
        verbose=False,
    )
    task = Task(
        description=f"Classify this message: {user_message!r}",
        agent=agent,
        expected_output=f"One of: {INTENT_MORTGAGE}, {INTENT_INCIDENT}, {INTENT_UNKNOWN}",
    )
    result = Crew(agents=[agent], tasks=[task], verbose=False).kickoff()
    raw = str(result).strip().lower()
    if INTENT_MORTGAGE in raw:
        return INTENT_MORTGAGE
    if INTENT_INCIDENT in raw:
        return INTENT_INCIDENT
    return INTENT_UNKNOWN
