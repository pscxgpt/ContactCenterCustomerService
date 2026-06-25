"""
Intent registry for the tiered router.

Each intent declares:
  - keywords : high-precision substrings for the Tier-0 deterministic shortcut
  - exemplars: example phrasings embedded for the Tier-1 semantic classifier

Adding a new specialist = adding an entry here (no retraining, no prompt edits).
"""
import unicodedata

from config.settings import INTENT_MORTGAGE, INTENT_INCIDENT


def normalize(text: str) -> str:
    """Lowercase + strip accents, so 'hipoteca' == 'Hipóteca' for matching."""
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


INTENTS = {
    INTENT_MORTGAGE: {
        "keywords": [
            "hipoteca", "hipotecaria", "prestamo para la vivienda", "tipo de interes",
            "euribor", "tin", "tae", "ltv", "amortizar", "amortizacion", "cuota mensual",
        ],
        "exemplars": [
            "Quiero pedir una hipoteca para comprar un piso",
            "Me gustaría simular una hipoteca a 30 años",
            "¿Qué cuota tendría una hipoteca de 200.000 euros?",
            "¿Qué tipo de interés ofrecéis en las hipotecas fijas?",
            "Necesito financiación para comprar una vivienda",
            "¿Cuánto pagaría al mes por una hipoteca variable?",
            "Quiero información sobre las condiciones de vuestras hipotecas",
            "Estoy pensando en comprar casa y necesito un préstamo hipotecario",
            "¿Me conviene más una hipoteca fija o mixta?",
            "Quiero saber si me concederíais una hipoteca con mis ingresos",
        ],
    },
    INTENT_INCIDENT: {
        "keywords": [
            "tarjeta", "fraude", "estafa", "cargo", "transferencia", "no reconozco",
            "robada", "robaron", "bloquea", "bloquear", "incidencia", "reclamacion",
            "duplicado", "no puedo acceder", "contrasena",
        ],
        "exemplars": [
            "Me han robado la tarjeta y quiero bloquearla",
            "Tengo un cargo en mi cuenta que no reconozco",
            "No me ha llegado una transferencia que me debían hacer",
            "Quiero poner una reclamación por un cobro indebido",
            "Creo que he sido víctima de un fraude bancario",
            "No puedo acceder a mi banca online",
            "He perdido la tarjeta de débito, ¿qué hago?",
            "Quiero disputar una transacción de mi cuenta",
            "Mi cuenta aparece bloqueada y no sé por qué",
            "He olvidado la contraseña de acceso a la app",
        ],
    },
}

# Tier-0: explicit request to talk to a person → straight to human handoff.
HUMAN_PHRASES = [
    "hablar con una persona", "una persona real", "un humano", "agente humano",
    "operador", "hablar con un gestor", "atencion al cliente real", "persona de verdad",
]
