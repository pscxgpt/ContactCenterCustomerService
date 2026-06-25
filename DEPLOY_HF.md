# 🚀 Desplegar la demo en Hugging Face Spaces

Publica la app como **enlace persistente** para que cualquiera (también alguien no técnico) la pruebe desde el navegador, con voz incluida. El plan **CPU basic (gratis)** tiene ~16 GB de RAM, suficiente para el stack (torch + sentence-transformers + CrewAI).

> El `README.md` ya incluye la cabecera YAML que HF necesita (`sdk: streamlit`, `app_file: ui/app.py`).
>
> **Importante — índice FAISS:** HF **rechaza archivos binarios** en un push normal (pide Xet/LFS). Para evitarlo, **no subimos el índice**: la app lo **construye al arrancar** desde el CSV (que es texto y sí se sube). Por eso el push al Space se hace desde una **rama limpia sin el binario** (ver paso 2). En GitHub el índice sigue versionado como hasta ahora.

---

## 1. Crear el Space
1. Entra en <https://huggingface.co/new-space> (crea una cuenta gratis si no tienes).
2. **Owner / Space name:** p. ej. `tu-usuario/contact-center-ia`.
3. **SDK:** `Streamlit`.
4. **Hardware:** `CPU basic · Free`.
5. **Visibility:** `Public` para poder compartir el enlace (o `Private` y añadir al revisor como colaborador).
6. Crea el Space (HF crea un repo git vacío con un README por defecto).

## 2. Subir el código (rama limpia sin el índice binario)
Crea un **token de escritura** en <https://huggingface.co/settings/tokens> (rol *Write*). Luego, desde la raíz del proyecto:

```bash
# 1) remoto del Space (si no lo tienes ya)
git remote add space https://huggingface.co/spaces/<TU_USUARIO>/<NOMBRE_SPACE>

# 2) rama de despliegue: historial nuevo (huérfano) SIN el índice binario
git checkout --orphan hf-deploy
git rm -r --cached knowledge_base/vector_store      # quita el binario del commit
echo "knowledge_base/vector_store/" >> .gitignore    # que no se vuelva a añadir
git add -A
git commit -m "Deploy a HF Spaces (índice construido en runtime)"

# 3) push autenticando con el token en la URL (evita el prompt de contraseña)
git push "https://<TU_USUARIO>:<TOKEN>@huggingface.co/spaces/<TU_USUARIO>/<NOMBRE_SPACE>" hf-deploy:main --force

# 4) vuelve a main (queda intacta, con el índice versionado)
git checkout main
```
- El token va en la URL solo para este push; no se guarda en el remoto. Puedes **revocarlo** después.
- `--force` reemplaza el commit inicial (README por defecto) del Space; es seguro porque está vacío.

## 3. Configurar el secreto (clave de Groq)
En la página del Space → **Settings → Variables and secrets → New secret**:
- **Name:** `GROQ_API_KEY`
- **Value:** tu clave de Groq

El código la lee con `os.getenv("GROQ_API_KEY")`, así que basta con esto (no subas el `.env`).

## 4. Esperar el build
- HF instala `requirements.txt` (torch + sentence-transformers tardan unos minutos la **primera** vez).
- La **primera consulta de incidencia** descarga el modelo de embeddings (~470 MB) **y construye el índice FAISS** desde el CSV (989 vectores, unos segundos). A partir de ahí va rápido (cacheado en memoria mientras el Space siga vivo).

## 5. Compartir
- Enlace: `https://huggingface.co/spaces/<TU_USUARIO>/contact-center-ia`.
- El **micrófono funciona** porque HF sirve por HTTPS. El revisor solo tiene que abrir el enlace, permitir el micro y hablar (o escribir).

---

## Notas y resolución de problemas
- **Coste:** cada interacción consume tu cuota de Groq (LLM + Whisper STT). Para un revisor puntual es mínimo; **no publiques el enlace en abierto**.
- **edge-tts (voz de salida)** llama a un servicio de Microsoft; HF permite salida a internet, así que funciona sin configuración.
- **Si el build falla por la versión de Streamlit:** ajusta `sdk_version` en la cabecera del `README.md` a una versión que HF ofrezca (p. ej. la última estable) y vuelve a empujar.
- **Reinicios:** el almacenamiento del Space es efímero; tras un *rebuild* se vuelve a descargar el modelo y a reconstruir el índice (normal).
- **Actualizar la demo:** repite el paso 2 (la rama `hf-deploy` se regenera desde `main`) y vuelve a hacer el `git push ... hf-deploy:main --force`.
