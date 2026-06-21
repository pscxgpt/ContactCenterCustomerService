"""
Financial calculator package — deterministic mortgage tools for CrewAI agents.

Tools:
  1. MortgageCalculatorTool     — Cuota mensual, total devuelto e intereses
  2. LTVCalculatorTool          — Loan-To-Value ratio
  3. CreditRatingTool           — Scoring interno de riesgo del cliente
  4. BonificationCalculatorTool — TAE final tras bonificaciones por productos
  5. MortgageSimulatorTool      — Escenarios: subida Euríbor, amortización parcial, esfuerzo
"""

from tools.financial_calculator.mortgage_calculator import MortgageCalculatorTool
from tools.financial_calculator.ltv_calculator import LTVCalculatorTool
from tools.financial_calculator.credit_rating import CreditRatingTool
from tools.financial_calculator.bonification_calculator import BonificationCalculatorTool
from tools.financial_calculator.mortgage_simulator import MortgageSimulatorTool

__all__ = [
    "MortgageCalculatorTool",
    "LTVCalculatorTool",
    "CreditRatingTool",
    "BonificationCalculatorTool",
    "MortgageSimulatorTool",
]
