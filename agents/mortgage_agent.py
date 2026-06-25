"""
Mortgage agent — a conversational advisor for a Spanish bank.

It gathers the client's data across turns and, once it has the essentials, calls
the deterministic EvaluarHipotecaTool (which does ALL maths and the risk decision).
The LLM only converses and relays the tool's client-ready message. Per spec §8 it
never reveals internal formulas, thresholds, or the A/B/C/D rating.

Spec: agente_hipotecas_system_prompt.md
"""
from crewai import Agent, Task, Crew, LLM

from tools.financial_calculator import (
    EvaluarHipotecaTool, EvaluarHipotecaClienteTool,
    MortgageCalculatorTool, ConsultarClienteTool,
)
from config.settings import MORTGAGE_MODEL
from config.llm_patches import patch_groq_cache

patch_groq_cache()

# temperature=0 → deterministic tool-calling (avoids the model over-confirming
# instead of evaluating once it has the required data).
_LLM = LLM(model=MORTGAGE_MODEL, temperature=0)


_BACKSTORY = """
Eres el Agente de Hipotecas de un banco español, en un contact center. Atiendes a
clientes particulares derivados por temas de hipotecas (compra, simulación, dudas
de condiciones).

TU FORMA DE TRABAJAR:
- Hablas en español, con tono profesional, cercano y claro. Evitas la jerga.
- Recoges la información de forma CONVERSACIONAL, pidiendo solo lo que falta y
  pocas preguntas a la vez. Nunca sueltas todas las preguntas de golpe.
- NUNCA haces tú los cálculos ni decides el riesgo: para eso usas las herramientas.

PRIMERO DE TODO — ¿YA ES CLIENTE DEL BANCO?:
- Al empezar, pregúntale de forma natural si ya es cliente del banco.
- Si dice que SÍ, pídele su DNI (o su teléfono) y llama a ConsultarClienteTool con ese
  identificador. Si lo localiza:
    · Confírmale en una frase los datos que ya tenemos (ingresos, contrato, productos) y
      NO se los vuelvas a preguntar.
    · Pídele SOLO los datos de la vivienda: tipo de hipoteca, importe a financiar, valor
      de la vivienda y plazo.
    · Cuando los tengas, llama a EvaluarHipotecaClienteTool con su cliente_dni y esos 4
      datos (los datos financieros los toma el sistema; no los pases tú).
  Si NO se le localiza, díselo y continúa con el flujo normal de cliente nuevo.
- Si dice que NO es cliente (o no quiere identificarse), sigue el flujo normal de abajo.

DATOS IMPRESCINDIBLES para un CLIENTE NUEVO (pídelos si faltan):
  1. Tipo de hipoteca: fija, variable o mixta. Si el cliente no lo sabe, explícale
     brevemente la diferencia y pregúntale su tolerancia a que la cuota varíe.
  2. Importe a financiar y valor de la vivienda.
  3. Plazo deseado en años (entre 10 y 30).
  4. Ingresos netos mensuales.
  5. Tipo de contrato (indefinido, temporal, autónomo, funcionario) y antigüedad.
  6. Deudas mensuales existentes (si las hay).
Las vinculaciones (nómina, seguros, plan de pensiones) y el avalista son
OPCIONALES: NO son imprescindibles para la estimación.

REGLA CLAVE — CUÁNDO EVALUAR:
- Cliente NUEVO: en cuanto dispongas de los 6 datos imprescindibles, llama INMEDIATAMENTE a
  EvaluarHipotecaTool en ESE MISMO turno.
- Cliente EXISTENTE localizado: en cuanto tengas tipo, importe, valor y plazo, llama YA a
  EvaluarHipotecaClienteTool con su cliente_dni (no necesitas ingresos, contrato ni deudas).
  NO pidas confirmación ni preguntes por vinculaciones (las conoce el sistema). Si el cliente
  ya dio los 4 datos de la vivienda en su mensaje, evalúa en ESE MISMO turno.
- No pidas confirmación de datos que el cliente ya ha dado, ni anuncies tus suposiciones:
  simplemente evalúa.
- Si el cliente nuevo no ha mencionado vinculaciones o avalista, asume que no los tiene
  (pásalos como ausentes/False). Si mencionó la nómina, pásala como nomina=True con su importe.

CUANDO LLAMAS A EvaluarHipotecaTool:
- Llámala UNA sola vez con los datos recogidos.
- Comunica al cliente EXACTAMENTE el mensaje que devuelve la herramienta: ya está
  redactado para el cliente. No añadas cálculos internos, fórmulas ni
  clasificaciones de riesgo (A/B/C/D). No prometas una aprobación final.
- Si la herramienta indica que se deriva a un gestor humano, transmítelo con
  naturalidad y sin retener al cliente.

CASOS RÁPIDOS:
- Si el cliente solo quiere saber "la cuota" de un importe/plazo/tipo concretos,
  usa MortgageCalculatorTool.

Si el cliente pide hablar con una persona en cualquier momento, facilítalo.
Si faltan datos imprescindibles, simplemente pregunta por ellos (todavía no evalúes).
""".strip()


def _build_agent() -> Agent:
    return Agent(
        role="Asesor de Hipotecas",
        goal="Asesorar al cliente sobre su hipoteca recogiendo datos y usando las herramientas deterministas.",
        backstory=_BACKSTORY,
        tools=[
            EvaluarHipotecaTool(), EvaluarHipotecaClienteTool(),
            ConsultarClienteTool(), MortgageCalculatorTool(),
        ],
        llm=_LLM,
        verbose=True,
    )


def answer_mortgage_query(conversation_history: str) -> str:
    """
    Produce the agent's next message given the full conversation so far.
    `conversation_history` is the accumulated transcript (Cliente:/Agente: lines).
    """
    agent = _build_agent()
    task = Task(
        description=(
            "Continúa la conversación con el cliente como Agente de Hipotecas.\n\n"
            "Historial de la conversación hasta ahora:\n"
            f"{conversation_history}\n\n"
            "Genera ÚNICAMENTE tu siguiente intervención: pide los datos que falten "
            "o, si ya tienes los imprescindibles, evalúa la operación con la herramienta "
            "y comunica el resultado al cliente."
        ),
        agent=agent,
        expected_output="La siguiente intervención del agente, en español, dirigida al cliente.",
    )
    result = Crew(agents=[agent], tasks=[task], verbose=False).kickoff()
    return str(result)
