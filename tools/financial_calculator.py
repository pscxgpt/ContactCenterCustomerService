"""
Deterministic mortgage financial calculator — no LLM math, pure Python.
Exposed as a CrewAI tool so agents can call it safely.
"""
import math
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class MortgageInput(BaseModel):
    principal: float = Field(..., description="Loan amount in euros.")
    annual_rate_pct: float = Field(..., description="Annual interest rate as a percentage (e.g. 3.5).")
    years: int = Field(..., description="Loan term in years.")


class MortgageCalculatorTool(BaseTool):
    name: str = "MortgageCalculatorTool"
    description: str = (
        "Calculates the monthly mortgage payment (cuota), total repayment, and total interest "
        "for a fixed-rate mortgage. Input: principal (€), annual_rate_pct (%), years."
    )
    args_schema: type[BaseModel] = MortgageInput

    def _run(self, principal: float, annual_rate_pct: float, years: int) -> str:
        monthly_rate = annual_rate_pct / 100 / 12
        n = years * 12

        if monthly_rate == 0:
            monthly_payment = principal / n
        else:
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)

        total_repayment = monthly_payment * n
        total_interest = total_repayment - principal

        return (
            f"Cuota mensual: {monthly_payment:.2f} €\n"
            f"Total a devolver: {total_repayment:.2f} €\n"
            f"Total intereses: {total_interest:.2f} €\n"
            f"(Capital: {principal:.2f} €, TIN: {annual_rate_pct}%, Plazo: {years} años)"
        )
