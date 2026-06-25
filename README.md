---
title: Contact Center IA Multiagente
emoji: 🏦
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.58.0
app_file: ui/app.py
pinned: false
short_description: Contact center bancario multiagente por voz
---

<!-- La cabecera YAML de arriba la usa Hugging Face Spaces (sdk + app_file: ui/app.py).
     Debe ir al principio del archivo. En GitHub es inofensiva. Guía: DEPLOY_HF.md -->

# 🤖 AI Mavericks | Reto 01: Contact Center Multiagente

Plataforma inteligente para un *Contact Center* bancario de banca de particulares. Transforma una línea única tradicional en un sistema **multiagente** que clasifica la intención del cliente y la deriva al agente especializado adecuado (Hipotecas o Atención al Cliente).

> Reto 01 de **AI Mavericks (Accenture Barcelona)**.

---

## 💡 Filosofía: "Mind + Tools" + Open-Source

1. **Cerebro + Herramientas (Mind + Tools):** el LLM **no** es la base de conocimiento ni una calculadora. Actúa solo como **motor de razonamiento y enrutamiento**: entiende la intención, extrae entidades y delega la ejecución en **herramientas deterministas en Python** (cálculos exactos) o en **búsqueda semántica local** (RAG). Esto elimina alucinaciones en cifras críticas.
2. **Modelos Open-Source:** diseñado para ejecutarse con modelos compactos (Llama 3.1 8B, Qwen 2.5 7B) desplegables *on-premise* / nube privada → **privacidad total de datos** y **OpEx mínimo**.

> ⚠️ **Nota de estado:** para la *demo*, los componentes en la nube se eligen por velocidad y fiabilidad en directo, pero todos tienen un **reemplazo local de un solo punto de cambio** (la tesis open-source): LLM → **Groq** (`llama-3.3-70b-versatile`) ⇒ Llama 3.1 8B / Qwen 2.5 7B; STT → **Groq Whisper** ⇒ `faster-whisper`; TTS → **edge-tts** ⇒ Piper. La lógica sensible (cálculos, decisiones de riesgo, RAG) ya corre **100 % local**. La migración a modelos locales es una tarea pendiente (ver [Roadmap](#-estado-del-proyecto)).

---

## 🏗️ Arquitectura

```text
[ Cliente ] 📞  ──habla──►  🎙️ STT (Groq Whisper)  ──┐
     │  (o escribe)                                   │ texto
     ▼                                                ▼
┌──────────────────────── ENRUTADOR POR NIVELES (cascada) ────────────────────────┐
│  Tier 0  reglas/keywords + "hablar con persona"      (0 ms, sin modelo)          │
│  Tier 1  clasificador semántico (embeddings locales) (~ms, sin tokens)           │
│  Tier 2  LLM (solo si Tier 1 no es concluyente)      (tokens, poco frecuente)    │
│  + sesión persistente (sticky) · clarificación · escalado a humano               │
└───────────────┬──────────────────────────────────────────────────────────────────┘
     │
     ├─► [ Hipotecas ]   ─► ┌────────────────────┐ ─► [ Motor de Asesoría ]
     │                      │  Agente Hipotecas  │      (Python determinista, Fase 1→3)
     │                      └────────────────────┘
     │
     ├─► [ Incidencias ] ─► ┌────────────────────┐ ─► [ RAG + gate de relevancia ]
     │                      │ Agente At. Cliente │      (FAISS local; si no hay
     │                      └────────────────────┘       match fiable → humano)
     │
     └─► [ Humano / Aclaración ]   (baja confianza, tema sensible o petición explícita)
                     │ respuesta (texto)
                     ▼
              🔊 TTS (edge-tts)  ──►  [ Cliente ] escucha
```

---

## 🧭 Enrutador por niveles (cascada)

El enrutador no manda **todo** al LLM: **escala por confianza**, de modo que la mayoría del tráfico se resuelve local y barato, y el LLM solo arbitra los casos ambiguos. Esta es la palanca de **coste/latencia/privacidad** que sostiene la tesis "Mind + Tools / open-source".

| Nivel | Qué hace | Coste |
|---|---|---|
| **Tier 0** | Reglas/keywords de alta precisión + petición explícita de persona | 0 ms, sin modelo |
| **Tier 1** | Clasificador semántico: similitud coseno contra *ejemplos* de cada intención (embeddings locales, los mismos del RAG) | ~ms, sin tokens |
| **Tier 2** | LLM con clasificación restringida — **solo** si Tier 1 no separa con margen suficiente | tokens, poco frecuente |

Cada decisión devuelve un `RouteDecision` estructurado (`route_to`, `tier`, `confidence`, `reason`) que la UI muestra como chip (`Tier 1 · hipotecas · 0.82`).

**Para un escenario real de call center:**
- **Sesión persistente (sticky):** una vez derivado a hipotecas, una repregunta ("¿y a 25 años?") **se queda** con el mismo agente; solo se reenruta si el cliente cambia de tema con confianza o pide un humano.
- **Aclaración y escalado a humano** como rutas de primera clase (baja confianza, tema sensible, petición explícita).
- **Escala por configuración:** añadir una intención = añadir una entrada en [`config/intents.py`](config/intents.py) (sin reentrenar ni reescribir prompts).
- **Camino de producción:** clasificador pequeño *fine-tuned* + observabilidad (logging de cada decisión, evaluación contra un set etiquetado, minería de errores de enrutado), servido con un modelo local (vLLM/TGI) y *session store* (Redis) para workers sin estado.

> 🌐 El enrutador (y el RAG) usan un **modelo de embeddings multilingüe** (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim). En español, las consultas dentro de alcance puntúan ~0.55-0.90 y las de fuera ~0.1-0.3, así que Tier 1 separa con fiabilidad y solo lo dudoso escala al LLM. Además habilita recuperación RAG **consulta en español → base de conocimiento en inglés**.

---

## 🎙️ Voz (canal de contact center)

El sistema es **conversacional por voz**: el cliente habla, el agente responde con voz, igual que en una llamada real — pero toda la inteligencia es la misma que en texto. La voz es una **capa fina e intercambiable** alrededor de los agentes ([`tools/voice.py`](tools/voice.py)); el enrutador y los agentes no saben cómo entra ni sale el audio.

```text
🎙️ grabar ─► STT (Groq Whisper) ─► route_turn() ─► agente ─► texto ─► TTS (edge-tts) ─► 🔊
```

| Pieza | Demo (nube) | Reemplazo local (producción) |
|---|---|---|
| **STT** (voz → texto) | Groq Whisper (`whisper-large-v3-turbo`), reutiliza `GROQ_API_KEY` | `faster-whisper` (offline) |
| **TTS** (texto → voz) | edge-tts, voz neuronal `es-ES-AlvaroNeural` | Piper (open-source, offline) |

- En [`ui/app.py`](ui/app.py) cada turno entra por **voz** (botón 🎙️ `st.audio_input`) o por **texto**; la respuesta hablada se reproduce automáticamente y hay un *toggle* en la barra lateral para activar/desactivar la voz.
- El reemplazo a modelos locales toca **solo [`tools/voice.py`](tools/voice.py)** (mismo patrón que el LLM). La verificación en directo de ambos tramos está en [`scripts/voice_smoke.py`](scripts/voice_smoke.py) (TTS → STT round-trip).

---

## 📁 Estructura del proyecto

```
ContactCenterCustomerService/
├── agents/                          # Agentes (CrewAI)
│   ├── router.py                    # Enrutador por niveles (cascada) + sesión sticky  ✅
│   ├── router_agent.py              # Clasificador LLM (Tier 2 del enrutador)
│   ├── mortgage_agent.py            # Agente de hipotecas conversacional  ✅
│   └── customer_service_agent.py    # Agente de incidencias (RAG + gate + memoria)  ✅
├── tools/
│   ├── financial_calculator/        # Lógica hipotecaria
│   │   ├── mortgage_core.py         # Núcleo determinista (LTV, TIN, rating…)  ✅
│   │   ├── advisory.py              # Motor de asesoría Fase 1→3  ✅
│   │   ├── advisory_tool.py         # EvaluarHipotecaTool + EvaluarHipotecaClienteTool  ✅
│   │   ├── client_lookup.py         # Búsqueda determinista de cliente existente  ✅
│   │   ├── client_tool.py           # ConsultarClienteTool (CrewAI)  ✅
│   │   ├── bonification_calculator.py / ltv_calculator.py / ...
│   │   └── _helpers.py              # Amortización francesa, TAE
│   ├── rag_search.py                # Búsqueda semántica FAISS + retrieve() con scores  ✅
│   ├── embeddings.py                # Modelo de embeddings compartido
│   └── voice.py                     # STT (Groq Whisper) + TTS (edge-tts)  ✅
├── knowledge_base/
│   ├── raw_docs/                    # Datasets: FAQ (banking_knowledge_base_1000.csv)
│   │                                #           + clientes (clientes_demo.csv)
│   └── vector_store/                # Índice FAISS generado (versionado)
├── scripts/
│   ├── build_index.py               # Construye el índice FAISS desde el CSV  ✅
│   └── voice_smoke.py               # Round-trip de voz TTS→STT (verifica STT y TTS)  ✅
├── ui/
│   ├── app.py                       # Chat multiagente por voz + texto (router → agentes)  ✅
│   ├── rag_explorer.py              # UI para verificar el RAG (sin LLM)  ✅
│   └── mortgage_chat.py             # Chat conversacional de hipotecas  ✅
├── config/
│   ├── settings.py                  # Modelos, rutas, voz, parámetros del spec y del enrutador
│   └── intents.py                   # Registro de intenciones (keywords + ejemplos)
├── tests/                           # Pruebas unitarias (64, deterministas)  ✅
├── main.py                          # CLI conversacional
├── smoke_test.py                    # Verificación del entorno (Groq, embeddings, CrewAI)
└── DEMO_RUNBOOK.md                  # Guion de la demo (escenas + frases verificadas)  ✅
```

**📂 Accesos directos:**
- **Datasets:** [`clientes_demo.csv`](knowledge_base/raw_docs/clientes_demo.csv) (clientes sintéticos para el lookup de hipotecas) · [`banking_knowledge_base_1000.csv`](knowledge_base/raw_docs/banking_knowledge_base_1000.csv) (base de conocimiento del RAG)
- **Agentes:** [router](agents/router.py) · [hipotecas](agents/mortgage_agent.py) · [atención al cliente](agents/customer_service_agent.py)
- **Lógica determinista:** [motor de asesoría](tools/financial_calculator/advisory.py) · [núcleo de cálculo](tools/financial_calculator/mortgage_core.py) · [lookup de clientes](tools/financial_calculator/client_lookup.py)
- **Config:** [`settings.py`](config/settings.py) · [`intents.py`](config/intents.py)
- **Docs:** [guion de demo](DEMO_RUNBOOK.md) · [despliegue en HF Spaces](DEPLOY_HF.md) · [spec de hipotecas](agente_hipotecas_system_prompt.md)

> 🎬 **Para la defensa en directo**, sigue [`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md): checklist previo, escenas guionizadas (hipoteca / cliente existente / incidencia / handoff / fuera de alcance), mensajes clave y plan B. Todas las frases están verificadas contra el sistema actual.

---

## 🛠️ Stack técnico

| Capa | Tecnología |
|---|---|
| Orquestación de agentes | CrewAI |
| LLM (dev) | Groq · `llama-3.3-70b-versatile` |
| Voz — STT / TTS | Groq Whisper (`whisper-large-v3-turbo`) / edge-tts (`es-ES-AlvaroNeural`) |
| Embeddings | `sentence-transformers` · `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, ES/EN) |
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

# 5b. (Opcional) Verifica el canal de voz (round-trip TTS→STT)
.venv\Scripts\python.exe scripts\voice_smoke.py

# 6a. App principal: chat multiagente por VOZ + texto (router → agentes)
.venv\Scripts\python.exe -m streamlit run ui\app.py

# 6b. Verifica el RAG visualmente (sin LLM)
.venv\Scripts\python.exe -m streamlit run ui\rag_explorer.py

# 6c. Chat conversacional del agente de hipotecas
.venv\Scripts\python.exe -m streamlit run ui\mortgage_chat.py

# 6d. CLI conversacional (router → agente)
.venv\Scripts\python.exe main.py
```

> El índice FAISS ya está versionado en `knowledge_base/vector_store/`, por lo que el paso 4 solo es necesario si cambias el dataset.

---

## 📊 Estado del proyecto

### ✅ Hecho y verificado
- **Canal de voz** ([`tools/voice.py`](tools/voice.py), [`ui/app.py`](ui/app.py)): conversación por voz extremo a extremo — 🎙️ grabar → STT (Groq Whisper) → enrutador → agente → TTS (edge-tts) → 🔊, con *toggle* de voz y entrada también por texto. Round-trip TTS→STT verificado en vivo ([`scripts/voice_smoke.py`](scripts/voice_smoke.py)).
- **Enrutador por niveles** ([`agents/router.py`](agents/router.py)): cascada Tier 0 (reglas) → Tier 1 (semántico) → Tier 2 (LLM) con gating por confianza, sesión *sticky*, aclaración y escalado a humano. Verificado en vivo y con tests offline.
- **Agente de Hipotecas — flujo de asesoría completo** ([`agente_hipotecas_system_prompt.md`](agente_hipotecas_system_prompt.md)):
  - Núcleo determinista ([`mortgage_core.py`](tools/financial_calculator/mortgage_core.py)): LTV, TIN final (base − bonificaciones + ajuste LTV, suelo 1,20%), cuota, ratio de esfuerzo `(cuota+deudas)/ingresos`, estabilidad laboral, historial, test de estrés, *rating* A/B/C/D con **regla de oro**, y rentabilidad.
  - Motor de asesoría Fase 1→3 ([`advisory.py`](tools/financial_calculator/advisory.py)): árbol de decisión, **motor de recomendaciones** (Modificar/Contratar/Eliminar), **escalado a gestor humano** (§7) y mensaje al cliente **§8-safe** (no revela rating/fórmulas).
  - Agente conversacional multi-turno ([`agents/mortgage_agent.py`](agents/mortgage_agent.py)) que recoge datos y llama a `EvaluarHipotecaTool` ([`advisory_tool.py`](tools/financial_calculator/advisory_tool.py)); los cálculos y la decisión los hace el código, no el LLM (`temperature=0`).
  - **Lookup de cliente existente** ([`client_lookup.py`](tools/financial_calculator/client_lookup.py) + [`ConsultarClienteTool`](tools/financial_calculator/client_tool.py)): si quien llama ya es cliente, da su DNI/teléfono y el sistema recupera su perfil (ingresos, contrato, antigüedad, deudas, productos vinculados) desde [`clientes_demo.csv`](knowledge_base/raw_docs/clientes_demo.csv). La evaluación usa [`EvaluarHipotecaClienteTool`](tools/financial_calculator/advisory_tool.py), que **lee los datos financieros directamente del sistema** (no pasan por el LLM) y aplica automáticamente las bonificaciones por vinculación. Más rápido, más realista y sin riesgo de transcripción.
- **Agente de Atención al Cliente — flujo de incidencias completo** ([`customer_service_agent.py`](agents/customer_service_agent.py)): mismo patrón *Mind + Tools* que hipotecas — la recuperación y la **decisión de escalado son deterministas**, el LLM solo redacta. (1) `retrieve()` ([`rag_search.py`](tools/rag_search.py)) devuelve los mejores resultados con *score* de relevancia; (2) si el mejor está por debajo de `RAG_MIN_RELEVANCE` (0,12, calibrado) → **escalado a humano** verbatim, sin improvisar; (3) si pasa el filtro, el LLM responde **solo** desde el contexto recuperado y con **memoria conversacional**, y admite no saber en vez de inventar. **Estilo de llamada:** respuestas breves y directas; el agente **es** la línea de atención, así que nunca remite a "llamar a atención al cliente / a un número" — si no puede resolver, **pasa con un gestor**. Verificado en vivo (respuesta fundamentada / memoria / handoff / concisión).
- **Pipeline RAG completo**: ingesta → índice FAISS → búsqueda con relevancia coseno. Dataset actual: [`banking_knowledge_base_1000.csv`](knowledge_base/raw_docs/banking_knowledge_base_1000.csv) (989 Q&A en 10 secciones).
- **`RAGSearchTool`** con embeddings centralizados ([`tools/embeddings.py`](tools/embeddings.py)) para no divergir entre indexado y consulta.
- **UIs Streamlit**: [`app.py`](ui/app.py) (chat multiagente por **voz + texto** con enrutador, sesión sticky y chip de nivel), [`rag_explorer.py`](ui/rag_explorer.py) (verifica el RAG sin LLM) y [`mortgage_chat.py`](ui/mortgage_chat.py) (chat de hipotecas); booteadas con `AppTest`.
- **64 tests** deterministas ([`tests/`](tests/)) sobre el núcleo, el motor de asesoría, el enrutador, el *gate* de incidencias y el lookup de clientes; flujos verificados en vivo contra Groq.

### 📋 Pendiente (TODO)
- [ ] Migrar los componentes en la nube a **equivalentes locales open-source** (LLM → Llama 3.1 8B / Qwen 2.5 7B; STT → `faster-whisper`; TTS → Piper) → despliegue *on-premise*.
- [ ] Observabilidad del enrutador: logging de decisiones, evaluación contra set etiquetado y minería de errores de enrutado.
- [ ] [`credit_rating.py`](tools/financial_calculator/credit_rating.py) queda como **legado** (el rating oficial vive en [`mortgage_core.py`](tools/financial_calculator/mortgage_core.py)); decidir si retirarlo.
- [ ] (Opcional) Integración con n8n / Flowise (`start_n8n.bat`, `start_flowise.bat`).

---

## 📝 Notas

- **Dataset RAG:** [`banking_knowledge_base_1000.csv`](knowledge_base/raw_docs/banking_knowledge_base_1000.csv) (`Section, Question, Answer`, ~1000 filas, UTF-8) sustituye al antiguo `Dataset_Banking_chatbot.csv`. Está en **inglés**; gracias al modelo de embeddings multilingüe, una consulta en **español** recupera correctamente de la base en inglés, y el LLM responde en español.
- **Dataset de clientes:** [`clientes_demo.csv`](knowledge_base/raw_docs/clientes_demo.csv) (10 clientes sintéticos, clave por DNI y teléfono) alimenta el [lookup de cliente existente](tools/financial_calculator/client_lookup.py) del agente de hipotecas. DNIs útiles para la demo: `12345678Z` (perfil sólido y vinculado), `55667788B` (autónomo), `44556677D` (con impagos), `66778899G` (temporal, ingresos bajos).
- **Embeddings multilingües:** si cambias el modelo de embeddings, **reconstruye el índice** ([`scripts/build_index.py`](scripts/build_index.py)) — el espacio vectorial cambia aunque la dimensión siga siendo 384.
- **Voz:** la entrada por micrófono de [`ui/app.py`](ui/app.py) requiere navegador con permiso de micro; STT/TTS de la demo necesitan red (Groq / Microsoft edge-tts). Si fallan, la app **degrada a texto** sin romperse. Verifica los dos tramos en directo con [`scripts/voice_smoke.py`](scripts/voice_smoke.py).
- **Calibración de tipos (hipotecas):** los tipos del spec son de una época de Euríbor bajo. En [`settings.py`](config/settings.py) se usa `EURIBOR_ACTUAL = 1.20` para que la capa de rentabilidad (§5) sea coherente; cámbialo junto con los `TIN_BASE_*` si quieres un entorno de mercado distinto.
- `.env`, `.venv/`, cachés y la config local de herramientas están excluidos vía `.gitignore`.
