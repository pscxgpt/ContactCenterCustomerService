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
