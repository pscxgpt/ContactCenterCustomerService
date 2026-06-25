"""
Mortgage evaluation tools (CrewAI). Both run the full deterministic advisory
engine and return ONLY the §8-safe client message (no internal rating/score/
formulas); the LLM never does the math or the risk decision.

  • EvaluarHipotecaTool         — cliente NUEVO: the agent passes every datum.
  • EvaluarHipotecaClienteTool  — cliente EXISTENTE: pass only the DNI + the
                                  property data; the financials are read from the
                                  bank's records (so they never pass through the LLM).

Two tools (rather than one with optional fields) because Groq's strict tool-call
validation requires every property in a tool's schema to be present; a minimal
schema lets the client path omit the financial fields cleanly.
"""
from typing import Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from tools.financial_calculator.advisory import (
    MortgageProfile, evaluar_hipoteca, render_mensaje_cliente,
)
from tools.financial_calculator.client_lookup import buscar_cliente

_CLIENTE_NO_ENCONTRADO = (
    "No encuentro a ese cliente en el sistema. ¿Me confirmas el DNI o prefieres "
    "que tomemos los datos directamente?"
)


class EvaluarHipotecaInput(BaseModel):
    # ── Required ──
    producto: str = Field(..., description="Tipo de hipoteca: 'fija', 'variable' o 'mixta'.")
    importe_financiar: float = Field(..., description="Importe a financiar en euros.")
    valor_tasacion: float = Field(..., description="Valor de tasación de la vivienda en euros.")
    plazo_anios: int = Field(..., description="Plazo deseado en años (10-30).")
    ingresos_netos: float = Field(..., description="Ingresos netos mensuales del solicitante (suma de titulares).")
    contrato: str = Field("indefinido", description="indefinido / temporal / autonomo / funcionario.")
    antiguedad_anios: float = Field(0.0, description="Antigüedad laboral en años.")
    deudas_mensuales: float = Field(0.0, description="Cuotas/deudas mensuales existentes en euros.")
    # ── Optional context ──
    precio_compra: Optional[float] = Field(None, description="Precio de compra si difiere de la tasación.")
    autonomo_estable: bool = Field(True, description="Para autónomos: ingresos estables en los últimos 2 años.")
    impagos_activos: bool = Field(False, description="Impagos activos o recientes (< 2 años).")
    revolving_intensivo: bool = Field(False, description="Uso intensivo de tarjetas revolving o microcréditos.")
    sin_historial: bool = Field(False, description="Cliente joven sin historial crediticio previo.")
    avalista: bool = Field(False, description="Hay avalista o segundo titular.")
    # ── Vinculaciones ──
    nomina: bool = Field(False, description="Domiciliará la nómina.")
    nomina_importe_mensual: float = Field(0.0, description="Importe de la nómina mensual (€).")
    seguro_hogar: bool = Field(False, description="Contratará seguro de hogar con el banco.")
    seguro_vida: bool = Field(False, description="Contratará seguro de vida con el banco.")
    plan_pensiones: bool = Field(False, description="Abrirá plan de pensiones con el banco.")
    plan_aportacion_anual: float = Field(0.0, description="Aportación anual al plan de pensiones (€).")
    # ── Escalation triggers ──
    vivienda_habitual: bool = Field(True, description="Es vivienda habitual (False si segunda/no habitual).")
    caso_no_estandar: bool = Field(False, description="Circunstancias fuera de reglas estándar (herencia, ingresos en el extranjero, etc.).")
    solicita_humano: bool = Field(False, description="El cliente pide hablar con un gestor humano.")


class EvaluarHipotecaTool(BaseTool):
    name: str = "EvaluarHipotecaTool"
    description: str = (
        "Evalúa la hipoteca de un cliente NUEVO (no identificado): calcula tipo de interés, "
        "cuota y LTV, analiza el riesgo y devuelve una recomendación lista para el cliente. "
        "Úsala UNA sola vez cuando tengas producto, importe, valor de la vivienda, plazo, "
        "ingresos, contrato y antigüedad."
    )
    args_schema: Type[BaseModel] = EvaluarHipotecaInput
    # The tool's output IS already the client-ready, §8-safe message. Return it
    # verbatim as the agent's answer so the LLM cannot paraphrase it into an
    # approval promise or leak/omit the figures.
    result_as_answer: bool = True

    def _run(self, **kwargs) -> str:
        try:
            profile = MortgageProfile(**kwargs)
            result = evaluar_hipoteca(profile)
            return render_mensaje_cliente(result)
        except ValueError as e:
            return f"No he podido completar la simulación: {e}. ¿Puedes revisar los datos?"


class EvaluarHipotecaClienteInput(BaseModel):
    cliente_dni: str = Field(..., description="DNI o teléfono del cliente EXISTENTE (ya localizado con ConsultarClienteTool).")
    producto: str = Field(..., description="Tipo de hipoteca: 'fija', 'variable' o 'mixta'.")
    importe_financiar: float = Field(..., description="Importe a financiar en euros.")
    valor_tasacion: float = Field(..., description="Valor de tasación de la vivienda en euros.")
    plazo_anios: int = Field(..., description="Plazo deseado en años (10-30).")


class EvaluarHipotecaClienteTool(BaseTool):
    name: str = "EvaluarHipotecaClienteTool"
    description: str = (
        "Evalúa la hipoteca de un cliente EXISTENTE ya localizado con ConsultarClienteTool. "
        "Solo necesitas su DNI y los datos de la vivienda (producto, importe, valor, plazo): "
        "los datos financieros (ingresos, contrato, antigüedad, deudas, productos) los toma "
        "del sistema del banco. Devuelve la recomendación lista para el cliente."
    )
    args_schema: Type[BaseModel] = EvaluarHipotecaClienteInput
    result_as_answer: bool = True

    def _run(self, cliente_dni: str, producto: str, importe_financiar: float,
             valor_tasacion: float, plazo_anios: int) -> str:
        rec = buscar_cliente(cliente_dni)
        if rec is None:
            return _CLIENTE_NO_ENCONTRADO
        try:
            profile = MortgageProfile(
                producto=producto, importe_financiar=importe_financiar,
                valor_tasacion=valor_tasacion, plazo_anios=plazo_anios,
                **rec.to_profile_fields(),
            )
            return render_mensaje_cliente(evaluar_hipoteca(profile))
        except ValueError as e:
            return f"No he podido completar la simulación: {e}. ¿Puedes revisar los datos?"
