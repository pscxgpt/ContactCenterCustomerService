"""
LTVCalculatorTool — Loan-To-Value ratio and risk assessment.
"""
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class LTVInput(BaseModel):
    principal: float = Field(..., description="Loan amount requested in euros.")
    property_value: float = Field(..., description="Appraised property value in euros.")


class LTVCalculatorTool(BaseTool):
    name: str = "LTVCalculatorTool"
    description: str = (
        "Calculates the Loan-To-Value (LTV) ratio — the percentage of the property value "
        "that the mortgage covers. Also returns the required down-payment and a qualitative "
        "risk band (Low / Medium / High / Very High)."
    )
    args_schema: type[BaseModel] = LTVInput

    def _run(self, principal: float, property_value: float) -> str:
        if property_value <= 0:
            return "Error: El valor del inmueble debe ser mayor que 0."
        ltv_pct = (principal / property_value) * 100
        down_payment = property_value - principal

        # Risk bands commonly used in Spanish banking
        if ltv_pct <= 60:
            band = "Bajo"
            comment = "Excelente ratio. Margen de seguridad amplio."
        elif ltv_pct <= 80:
            band = "Medio"
            comment = "Rango habitual para primera vivienda. Condiciones estándar."
        elif ltv_pct <= 90:
            band = "Alto"
            comment = "Supera el 80 %. Es probable que se requieran avales o seguros adicionales."
        else:
            band = "Muy Alto"
            comment = "Financiación superior al 90 %. Riesgo elevado; aprobación poco habitual."

        return (
            f"━━━ LTV (Loan-To-Value) ━━━\n"
            f"  Capital solicitado:  {principal:,.2f} €\n"
            f"  Valor del inmueble:  {property_value:,.2f} €\n"
            f"  Entrada necesaria:   {down_payment:,.2f} €\n"
            f"  LTV:                 {ltv_pct:.1f} %\n"
            f"  Banda de riesgo:     {band}\n"
            f"  Observación:         {comment}"
        )
