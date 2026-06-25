"""
Entry point — conversational CLI for the multiagent contact center.

Routes the first message; if it's a mortgage enquiry it stays in a multi-turn
conversation with the mortgage agent (accumulating history). Incidents are
answered per message via the RAG customer-service agent.

Usage:
  python main.py                     # interactive REPL
  python main.py "una pregunta..."   # single message, then continue interactively
"""
import sys

import truststore
truststore.inject_into_ssl()

# Windows consoles default to cp1252 and choke on € / accents; force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except Exception:
    pass

from agents.router import route_turn, ROUTE_HUMAN, ROUTE_CLARIFY, ROUTE_UNKNOWN
from agents.mortgage_agent import answer_mortgage_query
from agents.customer_service_agent import answer_incident_query
from config.settings import INTENT_MORTGAGE, INTENT_INCIDENT

EXIT_WORDS = {"salir", "exit", "quit", "adios", "adiós"}


def main() -> None:
    print("🏦 Contact Center — banca de particulares (escribe 'salir' para terminar)\n")

    session: dict = {"active_intent": None}
    history_lines: list[str] = []

    # Optional first message from argv
    pending = " ".join(sys.argv[1:]).strip() or None

    while True:
        if pending is not None:
            user = pending
            pending = None
            print(f"Cliente: {user}")
        else:
            try:
                user = input("Cliente: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nHasta pronto.")
                return

        if not user:
            continue
        if user.lower() in EXIT_WORDS:
            print("Agente: Gracias por contactar con nosotros. ¡Hasta pronto!")
            return

        decision = route_turn(user, session)
        print(f"[Router] {decision.chip}  ({decision.reason})")
        history_lines.append(f"Cliente: {user}")

        if decision.route_to == INTENT_MORTGAGE:
            reply = answer_mortgage_query("\n".join(history_lines))
        elif decision.route_to == INTENT_INCIDENT:
            # Prior turns (history_lines already has the current "Cliente:" line).
            reply = answer_incident_query(user, "\n".join(history_lines[:-1]))
        elif decision.route_to == ROUTE_HUMAN:
            reply = "Te paso con un gestor humano que continuará atendiéndote. Un momento, por favor."
        elif decision.route_to == ROUTE_CLARIFY:
            reply = ("Para ayudarte mejor, ¿tu consulta es sobre una hipoteca o sobre "
                     "una incidencia de tu cuenta (tarjeta, transferencia, fraude...)?")
        else:  # ROUTE_UNKNOWN
            reply = ("Puedo ayudarte con hipotecas o con incidencias de tu cuenta. "
                     "¿Cuál es tu consulta?")

        print(f"Agente: {reply}\n")
        history_lines.append(f"Agente: {reply}")


if __name__ == "__main__":
    main()
