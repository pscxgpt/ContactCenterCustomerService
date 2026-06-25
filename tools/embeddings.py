"""
Single source of truth for the embedding model, shared by the index builder and
the RAG search tool. Normalized embeddings + cosine distance give intuitive
relevance scores in [0, 1].
"""
from functools import lru_cache

# Use the OS certificate store for SSL so loading the model from the HF hub works
# behind corporate proxies — from any entry point (scripts, UI, tests).
import truststore
truststore.inject_into_ssl()

from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
