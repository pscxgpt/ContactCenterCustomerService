"""Unit tests for the deterministic mortgage core (spec: agente_hipotecas_system_prompt.md)."""
import pytest

from tools.financial_calculator import mortgage_core as mc


# ── §3.4 Cuota ──────────────────────────────────────────────────
def test_cuota_known_value():
    # 200.000 € @ 3 % a 30 años ≈ 843,21 €/mes
    assert abs(mc.cuota_mensual(200_000, 3.0, 30) - 843.21) < 1.0


def test_cuota_zero_term_no_crash():
    # Regression: years=0 with nonzero rate must not raise ZeroDivisionError
    assert mc.cuota_mensual(100_000, 3.0, 0) == 0.0


# ── §3.2 LTV ────────────────────────────────────────────────────
def test_ltv_bands():
    assert mc.calcular_ltv(160_000, 200_000).letra == "A"      # 80 %
    assert mc.calcular_ltv(170_000, 200_000).letra == "B"      # 85 %
    assert mc.calcular_ltv(190_000, 200_000).letra == "C"      # 95 %
    r = mc.calcular_ltv(196_000, 200_000)                      # 98 %
    assert r.letra == "D" and r.financiable is False


def test_ltv_uses_lower_of_appraisal_and_price():
    r = mc.calcular_ltv(80_000, valor_tasacion=100_000, precio_compra=90_000)
    assert abs(r.ltv_pct - 88.89) < 0.1 and r.letra == "B"


def test_ltv_rejects_zero_value():
    with pytest.raises(ValueError):
        mc.calcular_ltv(100_000, 0)


# ── §3.3 TIN final ──────────────────────────────────────────────
def test_tin_base_no_bonif_no_penalty():
    r = mc.calcular_tin_final("fija", ltv_pct=70)
    assert r.tin_final == 2.75 and r.suelo_aplicado is False


def test_tin_bonif_and_ltv_penalty():
    # 2.75 − (0.30 nómina + 0.10 hogar) + 0.20 (LTV 85) = 2.55
    r = mc.calcular_tin_final(
        "fija", ltv_pct=85,
        nomina=True, nomina_importe_mensual=1300,
        seguro_hogar=True,
    )
    assert abs(r.tin_final - 2.55) < 1e-9
    assert r.ajuste_ltv == 0.20


def test_tin_floor_applied():
    # variable 1.80 − 0.65 (all bonifs) = 1.15 < floor 1.20
    r = mc.calcular_tin_final(
        "variable", ltv_pct=70,
        nomina=True, nomina_importe_mensual=1500,
        seguro_hogar=True, seguro_vida=True,
        plan_pensiones=True, plan_aportacion_anual=700,
    )
    assert r.tin_final == 1.20 and r.suelo_aplicado is True


def test_tin_nomina_below_threshold_not_applied():
    r = mc.calcular_tin_final("fija", ltv_pct=70, nomina=True, nomina_importe_mensual=1000)
    assert "nomina" not in r.bonificaciones


def test_tin_ltv_over_95_flags_derive():
    r = mc.calcular_tin_final("fija", ltv_pct=98)
    assert r.derivar_excepcional is True


# ── §4.2 Esfuerzo ───────────────────────────────────────────────
@pytest.mark.parametrize("cuota,deudas,ingresos,letra", [
    (800, 0, 3000, "A"),      # 26.7 %
    (900, 100, 3000, "B"),    # 33.3 %
    (1100, 100, 3000, "C"),   # 40.0 %
    (1300, 0, 3000, "D"),     # 43.3 %
])
def test_esfuerzo_bands(cuota, deudas, ingresos, letra):
    assert mc.calcular_esfuerzo(cuota, deudas, ingresos).letra == letra


# ── §4.3 Estabilidad ────────────────────────────────────────────
@pytest.mark.parametrize("contrato,ant,estable,letra", [
    ("funcionario", 0, True, "A"),
    ("indefinido", 3, True, "A"),
    ("indefinido", 1, True, "B"),
    ("autonomo", 3, True, "B"),
    ("autonomo", 1, True, "C"),
    ("autonomo", 5, False, "C"),
    ("temporal", 5, True, "C"),
    ("beca", 5, True, "C"),     # unknown → conservative
])
def test_estabilidad(contrato, ant, estable, letra):
    assert mc.calcular_estabilidad(contrato, ant, estable).letra == letra


# ── §4.4 Historial ──────────────────────────────────────────────
def test_historial_impagos():
    r = mc.evaluar_historial(impagos_activos=True)
    assert r.letra == "D" and r.flag_revision is True


def test_historial_revolving_downgrades():
    assert mc.evaluar_historial(revolving_intensivo=True).downgrade_niveles == 1


def test_historial_no_history_not_penalized():
    r = mc.evaluar_historial(sin_historial=True)
    assert r.letra == "A" and r.flag_revision is False


# ── §4.5 Test de estrés ─────────────────────────────────────────
def test_stress_flags_vulnerable():
    r = mc.test_estres(200_000, 2.0, 30, deudas_mensuales=0, ingresos_netos=2000)
    assert r.vulnerabilidad is True


def test_stress_safe_profile():
    r = mc.test_estres(100_000, 2.0, 30, deudas_mensuales=0, ingresos_netos=5000)
    assert r.vulnerabilidad is False


# ── §4.6 Rating + regla de oro ──────────────────────────────────
def _hist(**kw):
    return mc.evaluar_historial(**kw)


def test_rating_all_a():
    r = mc.calcular_rating("A", "A", "A", _hist(), vulnerabilidad=False)
    assert r.rating_global == "A" and r.flag_revision_humana is False


def test_rating_worst_factor_dominates():
    r = mc.calcular_rating("A", "C", "A", _hist(), vulnerabilidad=False)
    assert r.rating_global == "C" and r.flag_revision_humana is True


def test_rating_impagos_is_d():
    r = mc.calcular_rating("A", "A", "A", _hist(impagos_activos=True), vulnerabilidad=False)
    assert r.rating_global == "D" and r.flag_revision_humana is True


def test_rating_avalista_lifts_d_to_c():
    r = mc.calcular_rating("A", "A", "A", _hist(impagos_activos=True),
                           vulnerabilidad=False, avalista=True)
    assert r.rating_global == "C" and r.regla_oro_aplicada is True


def test_rating_revolving_downgrade():
    r = mc.calcular_rating("A", "A", "A", _hist(revolving_intensivo=True), vulnerabilidad=False)
    assert r.rating_global == "B"


def test_rating_vulnerability_forces_c():
    r = mc.calcular_rating("A", "A", "A", _hist(), vulnerabilidad=True)
    assert r.rating_global == "C"


# ── §5 Rentabilidad ─────────────────────────────────────────────
def test_rentabilidad_alta():
    r = mc.calcular_rentabilidad(
        tin_final=2.75, principal=200_000, years=30, rating_global="A",
        bonificaciones={"nomina": True, "seguro_hogar": True}, euribor=1.20,
    )
    assert r.clasificacion == "alta" and r.rentabilidad_estimada > 0


def test_rentabilidad_baja_when_high_risk():
    r = mc.calcular_rentabilidad(
        tin_final=2.75, principal=200_000, years=30, rating_global="C",
        bonificaciones={"nomina": True}, euribor=1.20,
    )
    assert r.clasificacion == "baja"


def test_rentabilidad_media_without_vinculaciones():
    r = mc.calcular_rentabilidad(
        tin_final=2.75, principal=200_000, years=30, rating_global="A",
        bonificaciones={}, euribor=1.20,
    )
    assert r.clasificacion == "media"
