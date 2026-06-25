"""
RAG search tool — semantic search over the local FAISS vector store built from
the banking FAQ dataset (Query/Response pairs).
"""
from __future__ import annotations
import os
import warnings
from dataclasses import dataclass
from functools import lru_cache
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS
from config.settings import VECTOR_STORE_PATH, RETRIEVAL_K
from tools.embeddings import get_embeddings


@lru_cache(maxsize=1)
def _load_store() -> FAISS:
    """Load the FAISS store once and cache it (the embeddings model is heavy).

    If the index isn't present, build it from the source CSV first. This lets a
    deploy ship only the dataset (text) and construct the vector store on first
    use — e.g. Hugging Face Spaces rejects committed binary indexes, so there the
    index is built at runtime instead of being versioned.
    """
    if not os.path.exists(VECTOR_STORE_PATH):
        from scripts.build_index import build
        build()
    return FAISS.load_local(VECTOR_STORE_PATH, get_embeddings(), allow_dangerous_deserialization=True)


@dataclass
class RAGHit:
    query: str
    response: str
    score: float  # cosine relevance in [0, 1]; higher = more relevant


def retrieve(query: str, k: int = RETRIEVAL_K) -> list[RAGHit]:
    """Structured retrieval primitive — returns scored hits (best first) so the
    caller can make a deterministic relevance decision (e.g. handoff gate)."""
    store = _load_store()  # builds the index on first use if it isn't present
    # Cosine relevance over normalized embeddings can be negative for unrelated
    # queries (that's exactly our off-topic signal); LangChain warns because it
    # expects [0, 1]. The ordering is still valid, so silence the noisy warning.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        results = store.similarity_search_with_relevance_scores(query, k=k)
    return [
        RAGHit(
            query=doc.metadata.get("query", ""),
            response=doc.metadata.get("response", doc.page_content),
            score=float(score),
        )
        for doc, score in results
    ]


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
        hits = retrieve(query, k=k)
        if not hits:
            return "No relevant information found in the knowledge base."

        return "\n\n".join(
            f"[{i}] (relevancia={h.score:.2f})\nP: {h.query}\nR: {h.response}"
            for i, h in enumerate(hits, 1)
        )
