import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ROUTER_MODEL = "groq/llama-3.3-70b-versatile"
MORTGAGE_MODEL = "groq/llama-3.3-70b-versatile"
CUSTOMER_SERVICE_MODEL = "groq/llama-3.3-70b-versatile"

# Embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Vector store
VECTOR_STORE_PATH = "knowledge_base/vector_store"
RAW_DOCS_PATH = "knowledge_base/raw_docs"

# Source FAQ dataset (Query,Response CSV)
FAQ_CSV_PATH = os.path.join(RAW_DOCS_PATH, "archive (1)", "Dataset_Banking_chatbot.csv")

# Retrieval
RETRIEVAL_K = 3

# Intents the router can classify
INTENT_MORTGAGE = "hipotecas"
INTENT_INCIDENT = "incidencias"
INTENT_UNKNOWN = "desconocido"

# Mortgage defaults
BASE_RATE_FIJO = 3.50       # TIN base tipo fijo (%)
BASE_RATE_VARIABLE = 4.50   # Euríbor actual + spread (%)
EURIBOR_ACTUAL = 3.50       # Euríbor a 12 meses (%)
SPREAD_VARIABLE = 1.00      # Diferencial sobre Euríbor (pp)

# CSV data paths
CLIENTS_CSV = os.path.join(RAW_DOCS_PATH, "archive (1)", "bank_clients.csv")
MORTGAGES_CSV = os.path.join(RAW_DOCS_PATH, "archive (1)", "active_mortgages.csv")
PENDING_CASES_CSV = os.path.join(RAW_DOCS_PATH, "archive (1)", "pending_cases.csv")
