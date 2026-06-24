"""End-to-end tests for the deterministic advisory engine (spec §3–§7)."""
import pytest

from tools.financial_calculator.advisory import (
    MortgageProfile, evaluar_hipoteca, render_mensaje_cliente, DECISION,
)


def _strong_profile(**over):
    """A clean, low-risk applicant (should land Rating A → ofertar)."""
    base = dict(
        producto="fija",
        importe_financiar=150_000,
        valor_tasacion=250_000,        # LTV 60 %
        plazo_anios=25,
        ingresos_netos=4_000,
        contrato="funcionario",
        antiguedad_anios=10,
        deudas_mensuales=0,
    )
    base.update(over)
    return MortgageProfile(**base)


def test_strong_profile_is_offered():
    r = evaluar_hipoteca(_strong_profile())
    assert r.rating.rating_global == "A"
    assert r.decision == "ofertar"
    assert r.escalar_humano is False


def test_grey_zone_escalates_and_has_recommendations():
    # High LTV (92 %) → factor C → zona gris → must derive + recommend
    r = evaluar_hipoteca(_strong_profile(
        importe_financiar=230_000, valor_tasacion=250_000,
    ))
    assert r.rating.rating_global == "C"
    assert r.decision == "zona_gris_derivar"
    assert r.escalar_humano is True
    assert len(r.recomendaciones) >= 1


def test_impagos_force_high_risk_and_escalation():
    r = evaluar_hipoteca(_strong_profile(impagos_activos=True))
    assert r.rating.rating_global == "D"
    assert r.decision == "no_viable"
    assert any("Impagos" in m for m in r.motivos_escalado)


def test_high_effort_is_not_viable():
    r = evaluar_hipoteca(_strong_profile(
        importe_financiar=300_000, valor_tasacion=600_000,  # LTV 50 % (A)
        ingresos_netos=1_500,                               # but effort huge
    ))
    assert r.esfuerzo.letra == "D"
    assert r.decision == "no_viable"


def test_client_message_hides_internal_rating():
    r = evaluar_hipoteca(_strong_profile(
        importe_financiar=230_000, valor_tasacion=250_000,
    ))
    msg = render_mensaje_cliente(r)
    # §8: never leak the internal letter grade or the word "rating"
    assert "rating" not in msg.lower()
    assert f"Rating: {r.rating.rating_global}" not in msg
    assert "estimación orientativa" in msg


def test_client_request_human_always_escalates():
    r = evaluar_hipoteca(_strong_profile(solicita_humano=True))
    assert r.escalar_humano is True
    assert any("gestor humano" in m for m in r.motivos_escalado)


def test_evaluar_hipoteca_tool_returns_safe_message():
    from tools.financial_calculator import EvaluarHipotecaTool
    tool = EvaluarHipotecaTool()
    out = tool._run(
        producto="fija", importe_financiar=150_000, valor_tasacion=250_000,
        plazo_anios=25, ingresos_netos=4_000, contrato="funcionario", antiguedad_anios=10,
    )
    assert "estimación orientativa" in out
    assert "rating" not in out.lower()


def test_recommendation_includes_debt_removal_when_debts_present():
    r = evaluar_hipoteca(_strong_profile(
        importe_financiar=230_000, valor_tasacion=250_000, deudas_mensuales=400,
    ))
    titulos = [rec.titulo.lower() for rec in r.recomendaciones]
    assert any("deuda" in t for t in titulos)
