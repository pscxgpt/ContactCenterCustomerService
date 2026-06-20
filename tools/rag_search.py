"""
RAG search tool — semantic search over the local FAISS vector store built from
the banking FAQ dataset (Query/Response pairs).
"""
from __future__ import annotations
import os
from functools import lru_cache
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS
from config.settings import VECTOR_STORE_PATH, RETRIEVAL_K
from tools.embeddings import get_embeddings


@lru_cache(maxsize=1)
def _load_store() -> FAISS:
    """Load the FAISS store once and cache it (embeddings model is heavy)."""
    return FAISS.load_local(VECTOR_STORE_PATH, get_embeddings(), allow_dangerous_deserialization=True)


class RAGSearchInput(BaseModel):
    query: str = Field(..., description="The customer's question or incident description.")
    k: int = Field(default=RETRIEVAL_K, description="Number of relevant FAQ entries to retrieve.")


class RAGSearchTool(BaseTool):
    name: str = "RAGSearchTool"
    description: str = (
        "Searches the bank's FAQ knowledge base for entries relevant to a customer "
        "question or incident. Returns the most similar question/answer pairs."
    )
    args_schema: type[BaseModel] = RAGSearchInput

    def _run(self, query: str, k: int = RETRIEVAL_K) -> str:
        if not os.path.exists(VECTOR_STORE_PATH):
            return "Knowledge base not found. Please run scripts/build_index.py first."

        store = _load_store()
        results = store.similarity_search_with_relevance_scores(query, k=k)
        if not results:
            return "No relevant information found in the knowledge base."

        blocks = []
        for i, (doc, score) in enumerate(results, 1):
            q = doc.metadata.get("query", "")
            a = doc.metadata.get("response", doc.page_content)
            blocks.append(f"[{i}] (relevancia={score:.2f})\nP: {q}\nR: {a}")
        return "\n\n".join(blocks)
