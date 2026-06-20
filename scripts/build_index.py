"""
Builds (or rebuilds) the FAISS vector index from the banking FAQ dataset
(a CSV with `Query` and `Response` columns).

Each Q&A pair becomes one atomic document: the query and response are embedded
together so the agent retrieves both the matching question and its answer.

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


def load_faq_documents(csv_path: str) -> list[Document]:
    df = pd.read_csv(csv_path, encoding="cp1252")
    df.columns = [c.strip() for c in df.columns]

    expected = {"Query", "Response"}
    if not expected.issubset(df.columns):
        raise ValueError(f"CSV must have columns {expected}, found {list(df.columns)}")

    df = df.dropna(subset=["Query", "Response"])
    df["Query"] = df["Query"].str.strip()
    df["Response"] = df["Response"].str.strip()
    df = df[(df["Query"] != "") & (df["Response"] != "")].drop_duplicates(subset=["Query"])

    docs = []
    for i, row in df.iterrows():
        content = f"Pregunta: {row['Query']}\nRespuesta: {row['Response']}"
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "query": row["Query"],
                    "response": row["Response"],
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
