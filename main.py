"""
Entry point — runs the full multiagent pipeline from the CLI for quick testing.
Usage:  python main.py "Quiero saber la cuota de una hipoteca de 200000 euros a 30 años al 3.5%"
"""
import sys
import truststore
truststore.inject_into_ssl()

from agents.router_agent import classify_intent
from agents.mortgage_agent import answer_mortgage_query
from agents.customer_service_agent import answer_incident_query
from config.settings import INTENT_MORTGAGE, INTENT_INCIDENT


def run(message: str) -> str:
    intent = classify_intent(message)
    print(f"\n[Router] Intent: {intent}")

    if intent == INTENT_MORTGAGE:
        return answer_mortgage_query(message)
    if intent == INTENT_INCIDENT:
        return answer_incident_query(message)
    return "Consulta no reconocida. Por favor contacta con tu oficina."


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hola, ¿qué servicios ofrecéis?"
    print(run(query))
