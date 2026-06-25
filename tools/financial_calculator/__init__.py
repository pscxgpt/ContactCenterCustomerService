"""
Financial calculator package — deterministic mortgage tools for CrewAI agents.

Tools:
  1. EvaluarHipotecaTool       — Motor de asesoría completo (Fase 1→3). Úsalo para
                                 evaluar una operación y obtener la recomendación.
  1b. ConsultarClienteTool      — Localiza a un cliente existente (DNI/teléfono) y devuelve
                                 su perfil financiero para pre-rellenar la evaluación.
  2. MortgageCalculatorTool     — Cuota mensual, total devuelto e intereses (cálculo rápido)
  3. LTVCalculatorTool          — Loan-To-Value ratio
  4. CreditRatingTool           — Scoring interno (legado; el rating oficial vive en mortgage_core)
  5. BonificationCalculatorTool — TIN/TAE final tras bonificaciones por productos
  6. MortgageSimulatorTool      — Escenarios: subida Euríbor, amortización parcial, esfuerzo

Deterministic logic (no CrewAI) lives in `mortgage_core` and `advisory`.
"""

from tools.financial_calculator.mortgage_calculator import MortgageCalculatorTool
from tools.financial_calculator.ltv_calculator import LTVCalculatorTool
from tools.financial_calculator.credit_rating import CreditRatingTool
from tools.financial_calculator.bonification_calculator import BonificationCalculatorTool
from tools.financial_calculator.mortgage_simulator import MortgageSimulatorTool
from tools.financial_calculator.advisory_tool import (
    EvaluarHipotecaTool, EvaluarHipotecaClienteTool,
)
from tools.financial_calculator.client_tool import ConsultarClienteTool
from tools.financial_calculator.client_lookup import buscar_cliente

__all__ = [
    "EvaluarHipotecaTool",
    "EvaluarHipotecaClienteTool",
    "ConsultarClienteTool",
    "buscar_cliente",
    "MortgageCalculatorTool",
    "LTVCalculatorTool",
    "CreditRatingTool",
    "BonificationCalculatorTool",
    "MortgageSimulatorTool",
]
