# 🎬 Guion de Demo — Contact Center Multiagente (AI Mavericks)

Guion para la defensa en directo. Las frases están **verificadas** contra el
sistema actual. Habla por el micro (🎙️) o, si prefieres, escríbelas en el chat:
el flujo es el mismo.

---

## 0. Antes de empezar (checklist, 2 min)

- [ ] `.venv` activado · `pip install -r requirements.txt`
- [ ] `.env` con `GROQ_API_KEY`
- [ ] Índice FAISS presente (ya versionado; si no: `python scripts\build_index.py`)
- [ ] **Verifica la voz:** `.venv\Scripts\python.exe scripts\voice_smoke.py` → debe imprimir `✅ Round-trip de voz OK`
- [ ] Lanza la app: `.venv\Scripts\python.exe -m streamlit run ui\app.py`
- [ ] Permiso de **micrófono** concedido en el navegador · **volumen** alto · toggle *"Leer las respuestas en voz alta"* activado
- [ ] Conexión a internet (en la demo, STT/TTS van por la nube)

---

## 1. Encuadre (15 s, antes de tocar nada)

> "Esto es un contact center bancario **por voz**. Una sola línea: el cliente
> habla, un **enrutador** decide qué agente especializado le atiende, y le
> responde por voz. Lo interesante está en cómo está diseñado por debajo para
> ser **fiable y escalable**."

---

## 2. Escenas (≈ 4 min)

### Escena A — Hipoteca por voz (asesoría completa)
🎙️ **Di:** *"Quiero una hipoteca fija de 200.000 euros para un piso de 250.000, a 30 años. Gano 3.000 netos al mes, contrato indefinido desde hace 5 años y no tengo deudas."*

✅ **Esperado:** evalúa al momento → **TIN ≈ 2,75 %**, **cuota ≈ 816 €/mes**, **LTV 80 %**, *"encaja bien con nuestras condiciones"*, y sugiere añadir vinculaciones. Termina con el aviso de *"estimación orientativa"*.

🗣️ **Mensaje:** "Los números **no los inventa el LLM** — los calcula un motor determinista en Python. El LLM solo conversa y recoge datos. Cero alucinaciones en cifras, y cumple normativa: **nunca revela el rating interno ni promete una aprobación**."

### Escena A2 — Cliente EXISTENTE (lookup en el dataset) 💡
🎙️ **Di:** *"Hola, ya soy cliente del banco, mi DNI es 12345678Z. Quiero una hipoteca fija de 200.000 euros para un piso de 250.000, a 30 años."*

✅ **Esperado:** el agente **localiza a Laura** en el sistema, confirma su perfil (nómina, seguro de hogar, ingresos, contrato) **sin volver a preguntarlo**, y evalúa al momento → **TIN ≈ 2,35 %** y cuota ≈ **775 €** (más bajo que el cliente nuevo: 2,75 %, 816 €).

🗣️ **Mensaje:** "Si ya eres cliente, no te pedimos lo que el banco ya sabe: con tu DNI recuperamos ingresos, contrato y productos del sistema. Sus **vinculaciones (nómina, seguro) bajan el tipo automáticamente** — de 2,75 % a 2,35 %. Y esos datos financieros **se leen directamente del sistema, no pasan por el LLM**: más rápido, más realista y sin riesgo de error."

> Otros DNIs de prueba en `clientes_demo.csv`: `55667788B` (autónomo, totalmente vinculado), `44556677D` (con impagos → caso a derivar), `66778899G` (temporal, ingresos bajos).

### Escena B — Incidencia por voz (RAG)
🎙️ **Di:** *"Me han robado la tarjeta, ¿qué hago?"*

✅ **Esperado:** respuesta **corta y directa**, estilo llamada (bloqueo por la app / te ayudo a bloquearla).

🗣️ **Mensaje:** "El agente busca en la **base de conocimiento (RAG local)** y responde **solo** con lo que encuentra."

### Escena C — No está en la base → pase a humano
🎙️ **Di:** *"He olvidado el PIN de mi tarjeta."*

✅ **Esperado:** *"…no tengo información para recuperar el PIN. **Te paso con un gestor**…"* — fíjate que **no** dice "llama a atención al cliente": él **es** esa línea.

🗣️ **Mensaje:** "La decisión de escalar es **determinista**, por umbral de relevancia. El cliente nunca recibe una respuesta inventada; si no hay respuesta fiable, va a una persona."

### Escena D — Fuera de alcance
🎙️ **Di:** *"¿Qué tiempo hará mañana en Barcelona?"*

✅ **Esperado:** pide aclaración / lo marca fuera de alcance (no fuerza un agente).

🗣️ **Mensaje:** "El enrutador **no mete todo a la fuerza** en un agente. Si no está claro, aclara o escala."

### Escena E — Petición explícita de persona (señala el chip 🧭)
🎙️ **Di:** *"Prefiero hablar con una persona."*

✅ **Esperado:** **Tier 0** → pase a humano inmediato.

🗣️ **Mensaje** (señalando el chip `🧭 Tier 0 · …`): "El chip muestra **qué nivel** del enrutador ha decidido y con **qué confianza**. Tier 0 son reglas: **0 ms, sin modelo**. Esto resuelve barato y rápido la mayor parte del tráfico; el LLM solo arbitra lo dudoso."

---

## 3. La tesis (mensajes clave para el cierre)

- **Mind + Tools:** el LLM razona y enruta; las **herramientas deterministas** hacen los cálculos y las decisiones de riesgo → fiabilidad y cumplimiento.
- **Enrutador por niveles (cascada):** la mayoría del tráfico se resuelve **local y barato**; el LLM solo arbitra lo ambiguo → coste/latencia/privacidad.
- **Nube para la demo, local para producción:** LLM, STT y TTS son **intercambiables** por equivalentes open-source *on-premise* (un único punto de cambio). La lógica sensible ya corre **100 % local** → privacidad total, OpEx mínimo.
- **Escala por configuración:** añadir un agente/intención = añadir una entrada (`config/intents.py`), sin reentrenar.

---

## 4. Plan B (si algo falla en directo)

| Falla | Qué hacer |
|---|---|
| Micro / STT no va | **Escribe** la frase en el chat — mismo flujo, la app degrada a texto sin romperse |
| No hay sonido | Desactiva *"Leer las respuestas en voz alta"*; se muestra el texto |
| Groq lento | Menciónalo: *"es el LLM de iteración; en producción es local"* y reintenta |
| Todo cae | Enseña `scripts\voice_smoke.py` (voz OK) y `pytest -q` (**58 tests** verde) como prueba de que las piezas funcionan |

---

## 5. Frases listas (copia/léelas en voz alta)

```
Hipoteca (nuevo):  Quiero una hipoteca fija de 200.000 euros para un piso de
                   250.000, a 30 años. Gano 3.000 netos al mes, contrato
                   indefinido desde hace 5 años y no tengo deudas.

Hipoteca (cliente): Hola, ya soy cliente del banco, mi DNI es 12345678Z.
                   Quiero una hipoteca fija de 200.000 euros para un piso de
                   250.000, a 30 años.

Incidencia:        Me han robado la tarjeta, ¿qué hago?

Pase a humano:     He olvidado el PIN de mi tarjeta.

Fuera de alcance:  ¿Qué tiempo hará mañana en Barcelona?

Hablar con persona: Prefiero hablar con una persona.
```
