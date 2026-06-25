# 🚀 Desplegar la demo en Hugging Face Spaces

Publica la app como **enlace persistente** para que cualquiera (también alguien no técnico) la pruebe desde el navegador, con voz incluida. El plan **CPU basic (gratis)** tiene ~16 GB de RAM, suficiente para el stack (torch + sentence-transformers + CrewAI).

> El `README.md` ya incluye la cabecera YAML que HF necesita (`sdk: streamlit`, `app_file: ui/app.py`). No hace falta `git-lfs`: el índice FAISS ocupa ~2 MB y ningún archivo supera los límites de HF.

---

## 1. Crear el Space
1. Entra en <https://huggingface.co/new-space> (crea una cuenta gratis si no tienes).
2. **Owner / Space name:** p. ej. `tu-usuario/contact-center-ia`.
3. **SDK:** `Streamlit`.
4. **Hardware:** `CPU basic · Free`.
5. **Visibility:** `Public` para poder compartir el enlace (o `Private` y añadir al revisor como colaborador).
6. Crea el Space (HF crea un repo git vacío con un README por defecto).

## 2. Subir el código
Desde la raíz del proyecto, añade el Space como remoto y empuja:
```bash
git remote add space https://huggingface.co/spaces/<TU_USUARIO>/contact-center-ia
git push space main
```
- Te pedirá usuario/clave de HF: usa tu usuario y un **Access Token** (con permiso *write*) creado en <https://huggingface.co/settings/tokens>.
- Este push **sobrescribe** el README por defecto del Space con el nuestro (que ya trae la cabecera correcta).

## 3. Configurar el secreto (clave de Groq)
En la página del Space → **Settings → Variables and secrets → New secret**:
- **Name:** `GROQ_API_KEY`
- **Value:** tu clave de Groq

El código la lee con `os.getenv("GROQ_API_KEY")`, así que basta con esto (no subas el `.env`).

## 4. Esperar el build
- HF instala `requirements.txt` (torch + sentence-transformers tardan unos minutos la **primera** vez).
- La **primera** consulta descarga el modelo de embeddings (~470 MB) → ~1 min; después va rápido (cacheado en memoria).

## 5. Compartir
- Enlace: `https://huggingface.co/spaces/<TU_USUARIO>/contact-center-ia`.
- El **micrófono funciona** porque HF sirve por HTTPS. El revisor solo tiene que abrir el enlace, permitir el micro y hablar (o escribir).

---

## Notas y resolución de problemas
- **Coste:** cada interacción consume tu cuota de Groq (LLM + Whisper STT). Para un revisor puntual es mínimo; **no publiques el enlace en abierto**.
- **edge-tts (voz de salida)** llama a un servicio de Microsoft; HF permite salida a internet, así que funciona sin configuración.
- **Si el build falla por la versión de Streamlit:** ajusta `sdk_version` en la cabecera del `README.md` a una versión que HF ofrezca (p. ej. la última estable) y vuelve a empujar.
- **Reinicios:** el almacenamiento del Space es efímero; tras un *rebuild* se vuelve a descargar el modelo (normal).
- **Actualizar la demo:** vuelve a hacer `git push space main` tras cada cambio.
