"""
Tests for the existing-client lookup and its integration with the mortgage
evaluation tool. All offline/deterministic (no LLM, no network).
"""
from tools.financial_calculator.client_lookup import buscar_cliente
from tools.financial_calculator.advisory_tool import EvaluarHipotecaClienteTool
from tools.financial_calculator.advisory import (
    MortgageProfile, evaluar_hipoteca, render_mensaje_cliente,
)

DNI = "12345678Z"  # Laura Gómez Ruiz: 2600 €, indefinido 6y, nómina + seguro hogar


def test_lookup_by_dni():
    r = buscar_cliente(DNI)
    assert r is not None and r.nombre == "Laura Gómez Ruiz"
    assert r.ingresos_netos == 2600 and r.contrato == "indefinido"
    assert r.nomina is True and r.seguro_hogar is True


def test_lookup_is_case_and_space_insensitive():
    assert buscar_cliente("  12345678z  ") is not None


def test_lookup_by_phone_last9():
    # Stored as "+34 600 111 222"; match on the national number.
    assert buscar_cliente("600111222").nombre == "Laura Gómez Ruiz"


def test_lookup_unknown_returns_none():
    assert buscar_cliente("00000000X") is None
    assert buscar_cliente("") is None


def test_eval_cliente_tool_uses_dataset():
    """EvaluarHipotecaClienteTool must equal evaluating the looked-up profile."""
    prop = dict(producto="fija", importe_financiar=200000, valor_tasacion=250000, plazo_anios=30)
    via_tool = EvaluarHipotecaClienteTool()._run(cliente_dni=DNI, **prop)

    r = buscar_cliente(DNI)
    profile = MortgageProfile(**prop, **r.to_profile_fields())
    expected = render_mensaje_cliente(evaluar_hipoteca(profile))

    assert via_tool == expected
    assert "TIN" in via_tool and "Cuota" in via_tool


def test_eval_cliente_tool_unknown_dni_message():
    out = EvaluarHipotecaClienteTool()._run(
        cliente_dni="00000000X", producto="fija",
        importe_financiar=200000, valor_tasacion=250000, plazo_anios=30,
    )
    assert "No encuentro a ese cliente" in out
