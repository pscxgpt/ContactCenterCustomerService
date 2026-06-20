"""Environment smoke-test for the ContactCenterCustomerService project.
Verifies imports + the three real runtime paths (Groq LLM, HF embeddings, CrewAI).
Run:  .venv\\Scripts\\python.exe smoke_test.py
"""
import truststore
truststore.inject_into_ssl()  # use Windows system cert store (corporate SSL)

import os
from dotenv import load_dotenv
load_dotenv()

results = []
def check(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"[ OK ] {name}")
    except Exception as e:
        results.append((name, False, repr(e)))
        print(f"[FAIL] {name}: {e!r}")

# 1. Plain imports of everything in requirements.txt
def _imports():
    import streamlit, gradio
    import langchain, langchain_groq, langchain_community, langchain_huggingface
    import crewai
    import sentence_transformers, faiss, pydantic
    import dotenv, pandas, PIL, requests
check("imports (all requirements)", _imports)

# 2. Groq LLM live call
def _groq():
    assert os.getenv("GROQ_API_KEY"), "GROQ_API_KEY missing from .env"
    from langchain_groq import ChatGroq
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    r = llm.invoke("Reply with the single word: pong")
    assert r.content.strip(), "empty response"
check("Groq LLM live call", _groq)

# 3. HuggingFace embeddings (sentence-transformers)
def _embed():
    from langchain_huggingface import HuggingFaceEmbeddings
    emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    v = emb.embed_query("hello world")
    assert len(v) == 384, f"unexpected dim {len(v)}"
check("HuggingFace embeddings", _embed)

# 4. CrewAI single-agent run (needs litellm + cache_breakpoint patch for Groq)
def _crew():
    import crewai.llms.cache as _c
    _c.mark_cache_breakpoint = lambda msg: msg  # Groq rejects cache_breakpoint field
    from crewai import Agent, Task, Crew
    a = Agent(role="Tester", goal="Say hi", backstory="You test things.",
              llm="groq/llama-3.3-70b-versatile", verbose=False)
    t = Task(description="Say the word hello.", agent=a, expected_output="one word")
    Crew(agents=[a], tasks=[t], verbose=False).kickoff()
check("CrewAI agent run", _crew)

print("\n" + "=" * 50)
ok = sum(1 for _, p, _ in results if p)
print(f"RESULT: {ok}/{len(results)} passed")
for name, passed, err in results:
    if not passed:
        print(f"  - {name}: {err}")
