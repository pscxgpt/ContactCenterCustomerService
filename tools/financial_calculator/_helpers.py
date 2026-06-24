"""
Shared helper functions for the financial calculator tools.
"""


def _calc_mortgage(
    principal: float, annual_rate_pct: float, years: int
) -> tuple[float, float, float]:
    """Return (monthly_payment, total_repayment, total_interest)."""
    monthly_rate = annual_rate_pct / 100 / 12
    n = years * 12
    if n == 0:
        return 0.0, 0.0, 0.0
    if monthly_rate == 0:
        monthly_payment = principal / n
    else:
        monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** n) / (
            (1 + monthly_rate) ** n - 1
        )
    total_repayment = monthly_payment * n
    total_interest = total_repayment - principal
    return monthly_payment, total_repayment, total_interest


def _approximate_tae(
    principal: float, monthly_payment: float, years: int
) -> float:
    """
    Approximate the TAE (Tasa Anual Equivalente) using Newton-Raphson.
    This is a simplified calculation (no commissions/insurance premiums).
    For full regulatory TAE, fees and linked insurance costs should be included.
    """
    n = years * 12
    # Initial guess
    r = 0.03 / 12  # Start with 3% annual

    for _ in range(200):
        if r <= 0:
            r = 1e-8
        # f(r) = P * r*(1+r)^n / ((1+r)^n - 1) - monthly_payment
        factor = (1 + r) ** n
        f_val = principal * r * factor / (factor - 1) - monthly_payment

        # f'(r) — simplified derivative
        df_num = principal * (
            factor * (factor - 1)
            - r * n * (1 + r) ** (n - 1)
        )
        df_den = (factor - 1) ** 2
        if abs(df_den) < 1e-15:
            break
        df_val = df_num / df_den

        if abs(df_val) < 1e-15:
            break
        r_new = r - f_val / df_val
        if abs(r_new - r) < 1e-12:
            r = r_new
            break
        r = r_new

    # Convert monthly rate to annual effective rate (TAE)
    tae = ((1 + r) ** 12 - 1) * 100
    return tae
