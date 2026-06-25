import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ROUTER_MODEL = "groq/llama-3.3-70b-versatile"
MORTGAGE_MODEL = "groq/llama-3.3-70b-versatile"
CUSTOMER_SERVICE_MODEL = "groq/llama-3.3-70b-versatile"

# Embeddings — multilingual (ES/EN) for the Spanish router + EN knowledge base.
# 384-dim, same as the previous all-MiniLM-L6-v2, so the vector store layout is unchanged.
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

# Vector store
VECTOR_STORE_PATH = "knowledge_base/vector_store"
RAW_DOCS_PATH = "knowledge_base/raw_docs"

# Source FAQ dataset (Section,Question,Answer CSV)
FAQ_CSV_PATH = os.path.join(RAW_DOCS_PATH, "banking_knowledge_base_1000.csv")

# Retrieval
RETRIEVAL_K = 3

# Intents the router can classify
INTENT_MORTGAGE = "hipotecas"
INTENT_INCIDENT = "incidencias"
INTENT_UNKNOWN = "desconocido"

# Router (tiered cascade) thresholds — tuned for the multilingual MiniLM cosine
# sims. With this model Spanish on-topic queries score ~0.55-0.90 and off-topic
# ~0.1-0.3, so the absolute threshold separates well; the margin is a secondary
# guard. Anything not clearly in-scope escalates to the Tier-2 LLM.
ROUTER_TIER1_HIGH = 0.55        # minimum top score to accept a Tier-1 match
ROUTER_TIER1_MARGIN = 0.08      # required gap over the 2nd-best intent
ROUTER_TIER1_LOW = 0.38         # below this → out-of-scope; between → clarify
ROUTER_STICKY_SWITCH_CONF = 0.60  # confidence needed to switch away from the active agent

# ── Mortgage rates & risk parameters ─────────────────────────────────
# Source of truth: agente_hipotecas_system_prompt.md (the advisory spec).
# CALIBRATION NOTE: the spec lists design-time reference rates from a
# low-Euríbor environment. They are kept verbatim per project decision. If you
# move to a current-market environment, raise TIN_BASE_* and EURIBOR_ACTUAL as a
# coherent set, otherwise the profitability layer (§5) can go negative because
# bank cost of funds (Euríbor + 0.40) would exceed the mortgage TIN.
EURIBOR_ACTUAL = 1.20            # Euríbor 12m (%) — variable/mixta tramos & cost of funds

# §3.3 TIN base por producto (primer tramo)
TIN_BASE_FIJA = 2.75             # %
TIN_BASE_VARIABLE = 1.80         # % primer año (luego Euríbor + SPREAD_VARIABLE)
TIN_BASE_MIXTA = 2.20            # % primeros 5 años (luego Euríbor + SPREAD_MIXTA)
SPREAD_VARIABLE = 0.65           # pp sobre Euríbor tras el primer año
SPREAD_MIXTA = 0.70              # pp sobre Euríbor tras el tramo fijo
TIN_FLOOR = 1.20                 # suelo mínimo del TIN_final (%)

# §3.3 Bonificaciones por vinculación (pp restados del TIN base)
BONIF_NOMINA = 0.30              # requiere nómina ≥ NOMINA_MIN_MENSUAL
BONIF_SEGURO_HOGAR = 0.10
BONIF_SEGURO_VIDA = 0.15
BONIF_PLAN_PENSIONES = 0.10      # requiere aportación ≥ PLAN_PENSIONES_MIN_ANUAL
NOMINA_MIN_MENSUAL = 1200.0      # €/mes
PLAN_PENSIONES_MIN_ANUAL = 600.0 # €/año

# §3.3 Penalización por LTV alto (pp sumados al TIN)
LTV_PENALTY_80_90 = 0.20
LTV_PENALTY_90_95 = 0.40
LTV_MAX_FINANCIABLE = 95.0       # > este % no se financia (salvo excepción)

# §4.2 Ratio de esfuerzo (bandas)
ESFUERZO_OPTIMO = 0.30           # ≤ 30 % óptimo
ESFUERZO_ACEPTABLE = 0.35        # 30–35 % aceptable
ESFUERZO_GRIS = 0.40             # 35–40 % zona gris ; > 40 % riesgo alto

# §4.5 Test de estrés
STRESS_TIN_DELTA = 1.00          # +1 pp al TIN
STRESS_INCOME_FACTOR = 0.80      # caída del 20 % de ingresos
STRESS_ESFUERZO_FLAG = 0.45      # > 45 % en cualquier escenario → vulnerabilidad

# §5 Estimación de rentabilidad
COSTE_FONDOS_SPREAD = 0.40       # coste financiación banco = Euríbor + 0.40
VALOR_VINC_ANUAL = {             # €/año por vinculación contratada
    "nomina": 80.0,
    "seguro_hogar": 150.0,
    "seguro_vida": 200.0,
    "plan_pensiones": 60.0,
}
FACTOR_RIESGO = {"A": 1.00, "B": 0.90, "C": 0.75, "D": 0.50}

# CSV data paths
CLIENTS_CSV = os.path.join(RAW_DOCS_PATH, "archive (1)", "bank_clients.csv")
MORTGAGES_CSV = os.path.join(RAW_DOCS_PATH, "archive (1)", "active_mortgages.csv")
PENDING_CASES_CSV = os.path.join(RAW_DOCS_PATH, "archive (1)", "pending_cases.csv")
