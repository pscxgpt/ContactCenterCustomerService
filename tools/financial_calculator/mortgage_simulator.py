"""
MortgageSimulatorTool — Escenarios: subida Euríbor, amortización parcial, esfuerzo.
"""
import math
from typing import Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from tools.financial_calculator._helpers import _calc_mortgage


class SimulationInput(BaseModel):
    principal: float = Field(..., description="Loan amount in euros.")
    annual_rate_pct: float = Field(
        ..., description="Current annual interest rate as a percentage."
    )
    years: int = Field(..., description="Loan term in years.")
    net_monthly_income: float = Field(
        ..., description="Client's net monthly income in euros (for affordability ratios)."
    )
    is_variable_rate: bool = Field(
        False, description="True if the mortgage has a variable rate (e.g. Euríbor + spread)."
    )
    partial_amortization_amount: Optional[float] = Field(
        None,
        description="Optional: Amount in euros the client would use for a partial early repayment in year 5.",
    )
    euribor_stress_pp: float = Field(
        1.0,
        description="How many percentage points to add to the rate for the Euríbor stress scenario (default: 1.0 pp).",
    )


class MortgageSimulatorTool(BaseTool):
    name: str = "MortgageSimulatorTool"
    description: str = (
        "Runs three alternative scenarios for a mortgage: "
        "(1) Euríbor stress test — what happens if the rate rises; "
        "(2) Partial early repayment in year 5 — savings analysis; "
        "(3) Affordability — how much of net income the payment represents. "
        "Useful for variable-rate and fixed-rate mortgages."
    )
    args_schema: type[BaseModel] = SimulationInput

    def _run(
        self,
        principal: float,
        annual_rate_pct: float,
        years: int,
        net_monthly_income: float,
        is_variable_rate: bool = False,
        partial_amortization_amount: Optional[float] = None,
        euribor_stress_pp: float = 1.0,
    ) -> str:
        if net_monthly_income <= 0:
            return "Error: Los ingresos netos mensuales deben ser mayores que 0."

        base_payment, base_total, base_interest = _calc_mortgage(principal, annual_rate_pct, years)
        lines = ["━━━ Simulaciones / Escenarios Alternativos ━━━"]

        # ── Scenario 1: Euríbor stress ──
        lines.append("")
        lines.append("  ── Escenario 1: Subida del Euríbor ──")
        if is_variable_rate:
            stressed_rate = annual_rate_pct + euribor_stress_pp
            stressed_payment, stressed_total, stressed_interest = _calc_mortgage(
                principal, stressed_rate, years
            )
            delta_monthly = stressed_payment - base_payment
            delta_total = stressed_total - base_total
            lines.extend([
                f"  Tipo actual:         {annual_rate_pct:.2f} %",
                f"  Tipo estresado:      {stressed_rate:.2f} % (+{euribor_stress_pp:.1f} pp)",
                f"  Cuota actual:        {base_payment:,.2f} €/mes",
                f"  Cuota estresada:     {stressed_payment:,.2f} €/mes",
                f"  Incremento mensual:  +{delta_monthly:,.2f} €",
                f"  Coste extra total:   +{delta_total:,.2f} €",
            ])
            stressed_ratio = (stressed_payment / net_monthly_income) * 100
            if stressed_ratio > 35:
                lines.append(
                    f"  ⚠ La cuota estresada supondría el {stressed_ratio:.1f} % de los ingresos (> 35 %)."
                )
            else:
                lines.append(
                    f"  ✓ La cuota estresada supondría el {stressed_ratio:.1f} % de los ingresos (≤ 35 %)."
                )
        else:
            lines.append("  (Hipoteca a tipo fijo — este escenario no aplica directamente.)")
            lines.append(
                f"  A título informativo, si el tipo fuera {annual_rate_pct + euribor_stress_pp:.2f} %:"
            )
            stressed_rate = annual_rate_pct + euribor_stress_pp
            stressed_payment, _, _ = _calc_mortgage(principal, stressed_rate, years)
            lines.append(f"  La cuota sería {stressed_payment:,.2f} €/mes (vs {base_payment:,.2f} € actual).")

        # ── Scenario 2: Partial early repayment in year 5 ──
        lines.append("")
        lines.append("  ── Escenario 2: Amortización parcial en el año 5 ──")
        amort_amount = partial_amortization_amount if partial_amortization_amount else 10_000.0
        monthly_rate = annual_rate_pct / 100 / 12
        n_total = years * 12
        n_paid = 5 * 12  # 60 months already paid

        if n_paid >= n_total:
            lines.append("  (El plazo es ≤ 5 años; no aplica amortización en año 5.)")
        else:
            # Outstanding balance after 5 years
            if monthly_rate == 0:
                outstanding = principal - (base_payment * n_paid)
            else:
                outstanding = principal * ((1 + monthly_rate) ** n_paid) - base_payment * (
                    ((1 + monthly_rate) ** n_paid - 1) / monthly_rate
                )

            if amort_amount > outstanding:
                amort_amount = outstanding  # Can't pay more than you owe

            new_outstanding = outstanding - amort_amount
            remaining_months = n_total - n_paid

            # Option A: Reduce term (same payment)
            if new_outstanding <= 0:
                new_term_months_a = 0
                saved_months = remaining_months
                total_saved_a = base_payment * saved_months
            elif monthly_rate == 0:
                new_term_months_a = math.ceil(new_outstanding / base_payment)
                saved_months = remaining_months - new_term_months_a
                total_saved_a = base_payment * saved_months
            else:
                # n = -log(1 - outstanding*r/P) / log(1+r)
                ratio = 1 - (new_outstanding * monthly_rate / base_payment)
                if ratio > 0:
                    new_term_months_a = math.ceil(-math.log(ratio) / math.log(1 + monthly_rate))
                    saved_months = remaining_months - new_term_months_a
                    # Simpler savings approximation: difference in total payments
                    total_without = base_payment * remaining_months
                    total_with = base_payment * new_term_months_a
                    total_saved_a = total_without - total_with - amort_amount
                else:
                    new_term_months_a = remaining_months
                    saved_months = 0
                    total_saved_a = 0

            # Option B: Reduce payment (same term)
            if new_outstanding <= 0:
                new_payment_b = 0.0
            elif monthly_rate == 0:
                new_payment_b = new_outstanding / remaining_months
            else:
                new_payment_b = new_outstanding * (
                    monthly_rate * (1 + monthly_rate) ** remaining_months
                ) / ((1 + monthly_rate) ** remaining_months - 1)

            payment_reduction = base_payment - new_payment_b
            total_saved_b = payment_reduction * remaining_months - amort_amount

            lines.extend([
                f"  Capital pendiente (año 5):  {outstanding:,.2f} €",
                f"  Amortización anticipada:    {amort_amount:,.2f} €",
                f"  Nuevo capital pendiente:    {new_outstanding:,.2f} €",
                "",
                f"  Opción A — Reducir plazo (misma cuota):",
                f"    Plazo restante original:  {remaining_months} meses ({remaining_months // 12} años {remaining_months % 12} meses)",
                f"    Nuevo plazo restante:     {new_term_months_a} meses ({new_term_months_a // 12} años {new_term_months_a % 12} meses)",
                f"    Meses ahorrados:          {saved_months}",
                f"    Ahorro en intereses:      ~{max(total_saved_a, 0):,.2f} €",
                "",
                f"  Opción B — Reducir cuota (mismo plazo):",
                f"    Cuota actual:             {base_payment:,.2f} €/mes",
                f"    Nueva cuota:              {new_payment_b:,.2f} €/mes",
                f"    Reducción mensual:        {payment_reduction:,.2f} €/mes",
                f"    Ahorro en intereses:      ~{max(total_saved_b, 0):,.2f} €",
            ])

        # ── Scenario 3: Affordability ──
        lines.append("")
        lines.append("  ── Escenario 3: Esfuerzo sobre ingresos ──")
        ratio_pct = (base_payment / net_monthly_income) * 100
        remaining_income = net_monthly_income - base_payment

        if ratio_pct <= 25:
            assessment = "Muy cómodo — la cuota ocupa menos de una cuarta parte de los ingresos."
        elif ratio_pct <= 30:
            assessment = "Cómodo — margen holgado para otros gastos."
        elif ratio_pct <= 35:
            assessment = "Aceptable — en el límite recomendado por el Banco de España."
        elif ratio_pct <= 40:
            assessment = "Ajustado — supera la recomendación del 35 %. Conviene revisar."
        else:
            assessment = "Excesivo — riesgo alto de impago. Se desaconseja este nivel de endeudamiento."

        # Maximum recommended payment (35% of income)
        max_recommended = net_monthly_income * 0.35
        if monthly_rate == 0:
            max_principal = max_recommended * n_total
        else:
            max_principal = max_recommended * ((1 + monthly_rate) ** n_total - 1) / (
                monthly_rate * (1 + monthly_rate) ** n_total
            )

        lines.extend([
            f"  Cuota mensual:          {base_payment:,.2f} €",
            f"  Ingresos netos:         {net_monthly_income:,.2f} €/mes",
            f"  Ratio cuota/ingresos:   {ratio_pct:.1f} %",
            f"  Renta disponible:       {remaining_income:,.2f} €/mes",
            f"  Valoración:             {assessment}",
            "",
            f"  Referencia (límite 35 %):",
            f"    Cuota máxima recom.:  {max_recommended:,.2f} €/mes",
            f"    Capital máximo al {annual_rate_pct}% a {years} años: {max_principal:,.2f} €",
        ])

        return "\n".join(lines)
