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
├── agents/                      # Agentes (CrewAI)
│   ├── router_agent.py          # Clasifica intención (hipotecas / incidencias)
│   ├── mortgage_agent.py        # Agente de hipotecas (stub básico)
│   └── customer_service_agent.py# Agente de incidencias (RAG)
├── tools/                       # Herramientas deterministas
│   ├── financial_calculator.py  # Cálculo de cuota (amortización francesa)
│   ├── rag_search.py            # Búsqueda semántica FAISS  ✅
│   └── embeddings.py            # Modelo de embeddings compartido
├── knowledge_base/
│   ├── raw_docs/                # Dataset fuente (FAQ banca, CSV)
│   └── vector_store/            # Índice FAISS generado (versionado)
├── scripts/
│   └── build_index.py           # Construye el índice FAISS desde el CSV  ✅
├── ui/
│   ├── app.py                   # Chat multiagente completo (router → agentes)
│   └── rag_explorer.py          # UI para verificar el RAG (sin LLM)  ✅
├── config/settings.py           # Modelos, rutas, constantes
├── tests/                       # Pruebas unitarias
├── main.py                      # Punto de entrada CLI
└── smoke_test.py                # Verificación del entorno (Groq, embeddings, CrewAI)
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

# 5a. Verifica el RAG visualmente (sin LLM)
.venv\Scripts\python.exe -m streamlit run ui\rag_explorer.py

# 5b. O lanza el chat multiagente completo
.venv\Scripts\python.exe -m streamlit run ui\app.py
```

> El índice FAISS ya está versionado en `knowledge_base/vector_store/`, por lo que el paso 4 solo es necesario si cambias el dataset.

---

## 📊 Estado del proyecto

### ✅ Hecho y verificado
- **Pipeline RAG completo** (Atención al Cliente): ingesta del dataset FAQ → índice FAISS → búsqueda semántica con relevancia coseno `[0,1]`.
- **`RAGSearchTool`** integrada como herramienta CrewAI, con embeddings centralizados (`tools/embeddings.py`) para evitar divergencias entre indexado y consulta.
- **`scripts/build_index.py`**: construye el índice desde el CSV `Query/Response` (maneja codificación `cp1252`, deduplica).
- **`ui/rag_explorer.py`**: interfaz Streamlit para verificar la recuperación sin invocar el LLM (validada con `AppTest`).
- **Andamiaje del proyecto**: estructura de paquetes, `config/settings.py`, `.gitignore`.

### 🚧 Parcial / sin verificar end-to-end
- **Agente Enrutador** (`router_agent.py`): lógica de clasificación escrita, **falta validar con LLM en vivo**.
- **Agente de Atención al Cliente** (`customer_service_agent.py`): cableado al RAG, **falta prueba end-to-end** (router → RAG → respuesta).
- **`ui/app.py`** (chat multiagente completo): andamiaje listo, **sin verificar**.
- **Calculadora financiera** (`financial_calculator.py`): solo cuota por amortización francesa básica.

### 📋 Pendiente (TODO)

- [ ] **🔴 Agente de Hipotecas — lógica completa de negocio.**
  Implementar el flujo de 3 fases descrito en el system prompt aportado
  (`agente_hipotecas_system_prompt.md`):
  - **Fase 1 · Cálculo:** recogida de datos, LTV, TIN orientativo (base + bonificaciones por vinculación + ajuste por LTV, suelo 1,20%), cuota mensual.
  - **Fase 2 · Análisis de Riesgo:** ratio de esfuerzo, estabilidad laboral, historial, test de estrés, *rating* A/B/C/D.
  - **Capa intermedia · Rentabilidad** y **Fase 3 · Convicción/Rechazo** (motor de recomendaciones Modificar/Contratar/Eliminar).
  - Regla transversal de **escalado a gestor humano**.
  > ⚠️ Requiere ampliar `financial_calculator.py` con LTV, bonificaciones, rating y simulaciones. *(Spec entregada; pendiente de implementar — no codificado todavía.)*
- [ ] Migrar el LLM de Groq a un **modelo open-source local** (Llama 3.1 8B / Qwen 2.5 7B) → despliegue *on-premise*.
- [ ] Validación end-to-end del enrutador y los agentes con casos reales.
- [ ] Verificar y pulir `ui/app.py` (chat multiagente completo).
- [ ] Ampliar la base de conocimiento de incidencias y evaluar calidad del retrieval.
- [ ] Cobertura de tests (`tests/`) y añadir `pytest` a `requirements.txt`.
- [ ] (Opcional) Integración con n8n / Flowise (`start_n8n.bat`, `start_flowise.bat`).

---

## 📝 Notas

- El dataset FAQ actual (`Dataset_Banking_chatbot.csv`, 141 pares Q&A) está en **inglés**; los agentes están instruidos para responder en **español** (el LLM traduce). Pendiente decidir si traducir el dataset.
- `.env`, `.venv/`, cachés y la config local de herramientas están excluidos vía `.gitignore`.
