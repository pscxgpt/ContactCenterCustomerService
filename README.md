# 🤖 AI Mavericks | Reto 01: Contact Center Multiagente

Plataforma inteligente para un *Contact Center* bancario de banca de particulares. Transforma una línea única tradicional en un sistema **multiagente** que clasifica la intención del cliente y la deriva al agente especializado adecuado (Hipotecas o Atención al Cliente).

> Reto 01 de **AI Mavericks (Accenture Barcelona)**.

---

## 💡 Filosofía: "Mind + Tools" + Open-Source

1. **Cerebro + Herramientas (Mind + Tools):** el LLM **no** es la base de conocimiento ni una calculadora. Actúa solo como **motor de razonamiento y enrutamiento**: entiende la intención, extrae entidades y delega la ejecución en **herramientas deterministas en Python** (cálculos exactos) o en **búsqueda semántica local** (RAG). Esto elimina alucinaciones en cifras críticas.
2. **Modelos Open-Source:** diseñado para ejecutarse con modelos compactos (Llama 3.1 8B, Qwen 2.5 7B) desplegables *on-premise* / nube privada → **privacidad total de datos** y **OpEx mínimo**.

> ⚠️ **Nota de estado:** durante el desarrollo, los agentes usan **Groq (`llama-3.3-70b-versatile`)** como LLM por velocidad de iteración. La migración a un modelo open-source local es una tarea pendiente (ver [Roadmap](#-estado-del-proyecto)).

---

## 🏗️ Arquitectura

```text
[ Cliente ] 📞
     │
     ▼
┌────────────────────────────┐
│  Agente Enrutador (LLM)    │ ─► Clasifica intención
└────────────────────────────┘
     │
     ├─► [ Hipotecas ]   ─► ┌────────────────────┐ ─► [ Calculador Financiero ]
     │                      │  Agente Hipotecas  │      (Python determinista)
     │                      └────────────────────┘
     │
     └─► [ Incidencias ] ─► ┌────────────────────┐ ─► [ RAG: Base de Conocimiento ]
                            │ Agente At. Cliente │      (FAISS local)
                            └────────────────────┘
```

---

## 📁 Estructura del proyecto

```
ContactCenterCustomerService/
├── agents/                          # Agentes (CrewAI)
│   ├── router_agent.py              # Clasifica intención (hipotecas / incidencias)
│   ├── mortgage_agent.py            # Agente de hipotecas conversacional  ✅
│   └── customer_service_agent.py    # Agente de incidencias (RAG)
├── tools/
│   ├── financial_calculator/        # Lógica hipotecaria
│   │   ├── mortgage_core.py         # Núcleo determinista (LTV, TIN, rating…)  ✅
│   │   ├── advisory.py              # Motor de asesoría Fase 1→3  ✅
│   │   ├── advisory_tool.py         # EvaluarHipotecaTool (CrewAI)  ✅
│   │   ├── bonification_calculator.py / ltv_calculator.py / ...
│   │   └── _helpers.py              # Amortización francesa, TAE
│   ├── rag_search.py                # Búsqueda semántica FAISS  ✅
│   └── embeddings.py                # Modelo de embeddings compartido
├── knowledge_base/
│   ├── raw_docs/                    # Dataset fuente (banking_knowledge_base_1000.csv)
│   └── vector_store/                # Índice FAISS generado (versionado)
├── scripts/build_index.py           # Construye el índice FAISS desde el CSV  ✅
├── ui/
│   ├── app.py                       # Chat multiagente (router → agentes)
│   ├── rag_explorer.py              # UI para verificar el RAG (sin LLM)  ✅
│   └── mortgage_chat.py             # Chat conversacional de hipotecas  ✅
├── config/settings.py               # Modelos, rutas, parámetros del spec
├── tests/                           # Pruebas unitarias (47, deterministas)  ✅
├── main.py                          # CLI conversacional
└── smoke_test.py                    # Verificación del entorno (Groq, embeddings, CrewAI)
```

---

## 🛠️ Stack técnico

| Capa | Tecnología |
|---|---|
| Orquestación de agentes | CrewAI |
| LLM (dev) | Groq · `llama-3.3-70b-versatile` |
| Embeddings | `sentence-transformers` · `all-MiniLM-L6-v2` (384 dim) |
| Vector store | FAISS (local, CPU) |
| Framework RAG | LangChain |
| Interfaz | Streamlit |
| Tests | pytest (lógica determinista) |

---

## 🚀 Puesta en marcha

```bash
# 1. Entorno virtual + dependencias
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Configura las credenciales en .env
#    GROQ_API_KEY=tu_clave

# 3. (Opcional) Verifica el entorno
.venv\Scripts\python.exe smoke_test.py

# 4. Construye el índice FAISS desde el dataset
.venv\Scripts\python.exe scripts\build_index.py

# 5. (Opcional) Ejecuta los tests deterministas
.venv\Scripts\python.exe -m pytest -q

# 6a. Verifica el RAG visualmente (sin LLM)
.venv\Scripts\python.exe -m streamlit run ui\rag_explorer.py

# 6b. Chat conversacional del agente de hipotecas
.venv\Scripts\python.exe -m streamlit run ui\mortgage_chat.py

# 6c. CLI conversacional (router → agente)
.venv\Scripts\python.exe main.py
```

> El índice FAISS ya está versionado en `knowledge_base/vector_store/`, por lo que el paso 4 solo es necesario si cambias el dataset.

---

## 📊 Estado del proyecto

### ✅ Hecho y verificado
- **Agente de Hipotecas — flujo de asesoría completo** (`agente_hipotecas_system_prompt.md`):
  - Núcleo determinista (`mortgage_core.py`): LTV, TIN final (base − bonificaciones + ajuste LTV, suelo 1,20%), cuota, ratio de esfuerzo `(cuota+deudas)/ingresos`, estabilidad laboral, historial, test de estrés, *rating* A/B/C/D con **regla de oro**, y rentabilidad.
  - Motor de asesoría Fase 1→3 (`advisory.py`): árbol de decisión, **motor de recomendaciones** (Modificar/Contratar/Eliminar), **escalado a gestor humano** (§7) y mensaje al cliente **§8-safe** (no revela rating/fórmulas).
  - Agente conversacional multi-turno que recoge datos y llama a `EvaluarHipotecaTool` (los cálculos y la decisión los hace el código, no el LLM; `temperature=0`).
- **Pipeline RAG completo** (Atención al Cliente): ingesta → índice FAISS → búsqueda con relevancia coseno `[0,1]`. Dataset actual: `banking_knowledge_base_1000.csv` (989 Q&A en 10 secciones).
- **`RAGSearchTool`** con embeddings centralizados (`tools/embeddings.py`) para no divergir entre indexado y consulta.
- **UIs Streamlit**: `rag_explorer.py` (verifica el RAG sin LLM) y `mortgage_chat.py` (chat de hipotecas), ambas booteadas con `AppTest`.
- **47 tests** deterministas (`pytest`) sobre el núcleo y el motor de asesoría; flujo del agente verificado en vivo contra Groq.

### 🚧 Parcial / sin verificar end-to-end
- **Agente Enrutador** (`router_agent.py`): lógica de clasificación escrita, **falta validar con LLM en vivo**.
- **Agente de Atención al Cliente** (`customer_service_agent.py`): cableado al RAG; falta prueba end-to-end completa (router → RAG → respuesta).
- **`ui/app.py`** (chat multiagente unificado): andamiaje listo; el multi-turno de hipotecas aún no está integrado ahí (vive en `mortgage_chat.py`).

### 📋 Pendiente (TODO)
- [ ] Migrar el LLM de Groq a un **modelo open-source local** (Llama 3.1 8B / Qwen 2.5 7B) → despliegue *on-premise*.
- [ ] Integrar el flujo conversacional de hipotecas en `ui/app.py` y validar el enrutador en vivo.
- [ ] `credit_rating.py` queda como **legado** (el rating oficial vive en `mortgage_core`); decidir si retirarlo.
- [ ] (Opcional) Integración con n8n / Flowise (`start_n8n.bat`, `start_flowise.bat`).

---

## 📝 Notas

- **Dataset RAG:** `banking_knowledge_base_1000.csv` (`Section, Question, Answer`, ~1000 filas, UTF-8) sustituye al antiguo `Dataset_Banking_chatbot.csv`. Está en **inglés**; los agentes responden en **español** (el LLM traduce).
- **Calibración de tipos (hipotecas):** los tipos del spec son de una época de Euríbor bajo. En `settings.py` se usa `EURIBOR_ACTUAL = 1.20` para que la capa de rentabilidad (§5) sea coherente; cámbialo junto con los `TIN_BASE_*` si quieres un entorno de mercado distinto.
- `.env`, `.venv/`, cachés y la config local de herramientas están excluidos vía `.gitignore`.
