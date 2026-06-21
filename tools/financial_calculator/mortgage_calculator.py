"""
MortgageCalculatorTool — Cuota mensual, total devuelto e intereses.
"""
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from tools.financial_calculator._helpers import _calc_mortgage


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
        monthly_payment, total_repayment, total_interest = _calc_mortgage(
            principal, annual_rate_pct, years
        )
        return (
            f"Cuota mensual: {monthly_payment:,.2f} €\n"
            f"Total a devolver: {total_repayment:,.2f} €\n"
            f"Total intereses: {total_interest:,.2f} €\n"
            f"(Capital: {principal:,.2f} €, TIN: {annual_rate_pct}%, Plazo: {years} años)"
        )
