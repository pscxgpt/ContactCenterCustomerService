"""
RAG search tool — semantic search over the local FAISS vector store.
The index is built from documents in knowledge_base/raw_docs/.
"""
from __future__ import annotations
import os
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from config.settings import EMBEDDING_MODEL, VECTOR_STORE_PATH


class RAGSearchInput(BaseModel):
    query: str = Field(..., description="The customer's question or incident description.")
    k: int = Field(default=3, description="Number of relevant document chunks to retrieve.")


class RAGSearchTool(BaseTool):
    name: str = "RAGSearchTool"
    description: str = (
        "Searches the bank's internal knowledge base for procedures, FAQs, and policies "
        "relevant to a customer incident or question. Returns the top matching text chunks."
    )
    args_schema: type[BaseModel] = RAGSearchInput

    def _run(self, query: str, k: int = 3) -> str:
        if not os.path.exists(VECTOR_STORE_PATH):
            return "Knowledge base not found. Please run scripts/build_index.py first."

        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        store = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
        docs = store.similarity_search(query, k=k)

        if not docs:
            return "No relevant information found in the knowledge base."

        chunks = [f"[{i+1}] {d.page_content.strip()}" for i, d in enumerate(docs)]
        return "\n\n".join(chunks)
