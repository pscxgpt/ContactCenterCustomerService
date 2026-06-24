"""
Builds (or rebuilds) the FAISS vector index from the banking knowledge base
(a CSV with `Section`, `Question`, `Answer` columns).

Each Q&A pair becomes one atomic document: the question and answer are embedded
together so the agent retrieves both the matching question and its answer; the
section is kept as metadata.

Run:  python scripts/build_index.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import truststore
truststore.inject_into_ssl()

import pandas as pd
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from config.settings import EMBEDDING_MODEL, VECTOR_STORE_PATH, FAQ_CSV_PATH
from tools.embeddings import get_embeddings


def _read_csv(csv_path: str) -> pd.DataFrame:
    """Read the CSV, tolerating UTF-8 or Windows-1252 encodings."""
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(csv_path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {csv_path} as UTF-8/cp1252/latin-1.")


def load_faq_documents(csv_path: str) -> list[Document]:
    df = _read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    expected = {"Question", "Answer"}
    if not expected.issubset(df.columns):
        raise ValueError(f"CSV must have columns {expected}, found {list(df.columns)}")

    has_section = "Section" in df.columns
    df = df.dropna(subset=["Question", "Answer"])
    df["Question"] = df["Question"].str.strip()
    df["Answer"] = df["Answer"].str.strip()
    df = df[(df["Question"] != "") & (df["Answer"] != "")].drop_duplicates(subset=["Question"])

    docs = []
    for i, row in df.iterrows():
        section = str(row["Section"]).strip() if has_section else ""
        header = f"Sección: {section}\n" if section else ""
        content = f"{header}Pregunta: {row['Question']}\nRespuesta: {row['Answer']}"
        docs.append(
            Document(
                page_content=content,
                metadata={
                    # keep query/response keys for backward-compat with rag_search
                    "query": row["Question"],
                    "response": row["Answer"],
                    "section": section,
                    "source": os.path.basename(csv_path),
                    "row": int(i),
                },
            )
        )
    return docs


def build():
    print(f"Loading FAQ dataset from {FAQ_CSV_PATH} ...")
    docs = load_faq_documents(FAQ_CSV_PATH)
    if not docs:
        print("No valid Q&A rows found. Check the CSV.")
        return
    print(f"Loaded {len(docs)} Q&A pairs.")

    print(f"Embedding with {EMBEDDING_MODEL} ...")
    embeddings = get_embeddings()
    store = FAISS.from_documents(docs, embeddings, distance_strategy=DistanceStrategy.COSINE)

    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    store.save_local(VECTOR_STORE_PATH)
    print(f"Index saved to {VECTOR_STORE_PATH} ({len(docs)} vectors).")


if __name__ == "__main__":
    build()
