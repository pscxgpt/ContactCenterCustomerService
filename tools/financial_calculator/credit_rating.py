"""
CreditRatingTool — Scoring interno de riesgo del cliente.
"""
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class CreditRatingInput(BaseModel):
    monthly_payment: float = Field(
        ..., description="Monthly mortgage payment (cuota mensual) in euros."
    )
    net_monthly_income: float = Field(
        ..., description="Client's net monthly income in euros."
    )
    employment_type: str = Field(
        ...,
        description=(
            "Employment type. One of: 'indefinido' (permanent), 'temporal' (temporary), "
            "'autonomo' (self-employed), 'funcionario' (civil servant), 'desempleado' (unemployed)."
        ),
    )
    employment_years: float = Field(
        ..., description="Years of seniority in current job."
    )
    age: int = Field(..., description="Client's age in years.")
    loan_term_years: int = Field(..., description="Requested mortgage term in years.")


class CreditRatingTool(BaseTool):
    name: str = "CreditRatingTool"
    description: str = (
        "Produces an internal credit-risk score (0-100) for a mortgage applicant "
        "by combining: debt-to-income ratio (cuota/ingresos), employment stability, "
        "age-vs-term adequacy, and other factors. Returns score, rating letter, and "
        "a detailed breakdown."
    )
    args_schema: type[BaseModel] = CreditRatingInput

    def _run(
        self,
        monthly_payment: float,
        net_monthly_income: float,
        employment_type: str,
        employment_years: float,
        age: int,
        loan_term_years: int,
    ) -> str:
        # --- 1) Ratio cuota / ingresos (peso: 40 %) ---
        if net_monthly_income <= 0:
            return "Error: Los ingresos netos mensuales deben ser mayores que 0."
        dti_ratio = monthly_payment / net_monthly_income
        dti_pct = dti_ratio * 100

        if dti_ratio <= 0.25:
            dti_score = 40
            dti_comment = "Excelente — cuota inferior al 25 % de ingresos."
        elif dti_ratio <= 0.30:
            dti_score = 34
            dti_comment = "Bueno — cuota entre el 25 % y el 30 %."
        elif dti_ratio <= 0.35:
            dti_score = 26
            dti_comment = "Aceptable — cuota entre el 30 % y el 35 %."
        elif dti_ratio <= 0.40:
            dti_score = 16
            dti_comment = "Ajustado — cuota entre el 35 % y el 40 %. Riesgo moderado."
        else:
            dti_score = 6
            dti_comment = "Elevado — cuota superior al 40 % de los ingresos."

        # --- 2) Estabilidad laboral (peso: 30 %) ---
        emp_lower = employment_type.lower().strip()
        emp_base_scores = {
            "funcionario": 30,
            "indefinido": 25,
            "autonomo": 18,
            "temporal": 10,
            "desempleado": 2,
        }
        emp_score = emp_base_scores.get(emp_lower, 12)

        # Bonus by seniority (only if not unemployed)
        if emp_lower != "desempleado":
            if employment_years >= 10:
                emp_score = min(emp_score + 5, 30)
            elif employment_years >= 5:
                emp_score = min(emp_score + 3, 30)
            elif employment_years >= 2:
                emp_score = min(emp_score + 1, 30)

        emp_comment = f"Tipo: {employment_type}, antigüedad: {employment_years} años."

        # --- 3) Edad y plazo (peso: 20 %) ---
        age_at_end = age + loan_term_years
        if age_at_end <= 65:
            age_score = 20
            age_comment = f"Edad al finalizar: {age_at_end} años. Sin riesgo de jubilación."
        elif age_at_end <= 70:
            age_score = 14
            age_comment = f"Edad al finalizar: {age_at_end} años. Incluye algunos años post-jubilación."
        elif age_at_end <= 75:
            age_score = 8
            age_comment = f"Edad al finalizar: {age_at_end} años. Plazo se extiende bien pasada la jubilación."
        else:
            age_score = 3
            age_comment = f"Edad al finalizar: {age_at_end} años. Excesivo; difícil aprobación."

        # --- 4) Plazo (peso: 10 %) ---
        if loan_term_years <= 20:
            term_score = 10
            term_comment = "Plazo corto/medio — menor exposición temporal."
        elif loan_term_years <= 30:
            term_score = 7
            term_comment = "Plazo largo pero habitual en el mercado."
        else:
            term_score = 3
            term_comment = "Plazo superior a 30 años — riesgo temporal alto."

        # --- Total ---
        total_score = dti_score + emp_score + age_score + term_score

        # Rating letter
        if total_score >= 85:
            rating = "A+"
            verdict = "Perfil excelente. Aprobación muy probable con las mejores condiciones."
        elif total_score >= 70:
            rating = "A"
            verdict = "Perfil sólido. Aprobación probable con buenas condiciones."
        elif total_score >= 55:
            rating = "B"
            verdict = "Perfil aceptable. Aprobación posible; pueden exigirse garantías adicionales."
        elif total_score >= 40:
            rating = "C"
            verdict = "Perfil ajustado. Aprobación difícil sin mejoras (más entrada, aval, etc.)."
        else:
            rating = "D"
            verdict = "Perfil de alto riesgo. Aprobación muy improbable en condiciones estándar."

        return (
            f"━━━ Rating Crediticio Interno ━━━\n"
            f"  Puntuación total:     {total_score}/100   →  Rating: {rating}\n"
            f"  Veredicto:            {verdict}\n"
            f"\n"
            f"  ── Desglose ──\n"
            f"  1. Cuota/Ingresos:    {dti_pct:.1f} %  →  {dti_score}/40 pts\n"
            f"     {dti_comment}\n"
            f"  2. Estabilidad lab.:  {emp_score}/30 pts\n"
            f"     {emp_comment}\n"
            f"  3. Edad/Plazo:        {age_score}/20 pts\n"
            f"     {age_comment}\n"
            f"  4. Duración plazo:    {term_score}/10 pts\n"
            f"     {term_comment}"
        )
