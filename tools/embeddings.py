"""
Single source of truth for the embedding model, shared by the index builder and
the RAG search tool. Normalized embeddings + cosine distance give intuitive
relevance scores in [0, 1].
"""
from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
