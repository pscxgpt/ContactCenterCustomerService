"""
BonificationCalculatorTool — TAE final tras bonificaciones por productos vinculados.
"""
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from tools.financial_calculator._helpers import _calc_mortgage, _approximate_tae
from config import settings as S


class BonificationInput(BaseModel):
    base_annual_rate_pct: float = Field(
        ..., description="Base annual interest rate (TIN) as a percentage before bonifications."
    )
    principal: float = Field(..., description="Loan amount in euros.")
    years: int = Field(..., description="Loan term in years.")
    nomina_domiciliada: bool = Field(
        False, description="True if client will direct-deposit salary into the bank."
    )
    seguro_hogar: bool = Field(
        False, description="True if client will take out the bank's home insurance."
    )
    seguro_vida: bool = Field(
        False, description="True if client will take out the bank's life insurance."
    )
    plan_pensiones: bool = Field(
        False, description="True if client will open a pension plan with the bank (≥ 600 €/year)."
    )


class BonificationCalculatorTool(BaseTool):
    name: str = "BonificationCalculatorTool"
    description: str = (
        "Calculates the final interest rate and TAE after applying bonifications "
        "for linked products (nómina domiciliada, seguros, plan de pensiones, etc.). "
        "Shows the savings compared to the base rate."
    )
    args_schema: type[BaseModel] = BonificationInput

    def _run(
        self,
        base_annual_rate_pct: float,
        principal: float,
        years: int,
        nomina_domiciliada: bool = False,
        seguro_hogar: bool = False,
        seguro_vida: bool = False,
        plan_pensiones: bool = False,
    ) -> str:
        # Bonification discounts (pp) — spec §3.3, sourced from settings
        bonifications = []
        total_discount = 0.0

        products = [
            (nomina_domiciliada, S.BONIF_NOMINA, "Nómina domiciliada (≥ 1.200 €/mes)"),
            (seguro_hogar, S.BONIF_SEGURO_HOGAR, "Seguro de hogar"),
            (seguro_vida, S.BONIF_SEGURO_VIDA, "Seguro de vida"),
            (plan_pensiones, S.BONIF_PLAN_PENSIONES, "Plan de pensiones (≥ 600 €/año)"),
        ]

        for active, discount, name in products:
            if active:
                bonifications.append((name, discount))
                total_discount += discount

        # Apply the absolute TIN floor (spec §3.3)
        final_rate_pct = max(base_annual_rate_pct - total_discount, S.TIN_FLOOR)

        # Calculate cuotas for base and bonified rates
        base_payment, base_total, base_interest = _calc_mortgage(principal, base_annual_rate_pct, years)
        final_payment, final_total, final_interest = _calc_mortgage(principal, final_rate_pct, years)

        savings_monthly = base_payment - final_payment
        savings_total = base_total - final_total

        # Approximate TAE (simplified — assumes no additional fees)
        # For a more accurate TAE, commissions and insurance premiums should be included
        base_tae = _approximate_tae(principal, base_payment, years)
        final_tae = _approximate_tae(principal, final_payment, years)

        # Build output
        lines = [
            "━━━ Bonificaciones por Productos Vinculados ━━━",
            f"  TIN base:            {base_annual_rate_pct:.2f} %",
            f"  Descuento total:    -{total_discount:.2f} pp",
            f"  TIN bonificado:      {final_rate_pct:.2f} %",
            f"  TAE aprox. base:     {base_tae:.2f} %",
            f"  TAE aprox. bonif.:   {final_tae:.2f} %",
            "",
            "  ── Productos aplicados ──",
        ]

        if bonifications:
            for name, disc in bonifications:
                lines.append(f"    ✓ {name}: -{disc:.2f} pp")
        else:
            lines.append("    (Ningún producto vinculado seleccionado)")

        not_applied = [(name, disc) for active, disc, name in products if not active]
        if not_applied:
            lines.append("")
            lines.append("  ── Productos disponibles (no seleccionados) ──")
            for name, disc in not_applied:
                lines.append(f"    ○ {name}: -{disc:.2f} pp")

        lines.extend([
            "",
            "  ── Comparativa de cuotas ──",
            f"  Cuota sin bonif.:    {base_payment:,.2f} €/mes",
            f"  Cuota bonificada:    {final_payment:,.2f} €/mes",
            f"  Ahorro mensual:      {savings_monthly:,.2f} €",
            f"  Ahorro total vida:   {savings_total:,.2f} €",
        ])

        return "\n".join(lines)
