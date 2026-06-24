"""
mortgage_core.py — Deterministic mortgage logic. Single source of truth for the
advisory flow described in agente_hipotecas_system_prompt.md.

Pure Python: no LLM, no CrewAI, no I/O. Every numeric/business decision lives
here so it can be unit-tested and trusted ("Mind + Tools": the LLM never decides
these, the code does).

Spec coverage:
  §3.2 LTV · §3.3 TIN final · §3.4 cuota · §4.2 esfuerzo · §4.3 estabilidad
  §4.4 historial · §4.5 test de estrés · §4.6 rating + regla de oro · §5 rentabilidad

Internal grades (A/B/C/D, scores) are for internal use only; per spec §8 the
rendering layer decides what is shown to the client.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from config import settings as S
from tools.financial_calculator._helpers import _calc_mortgage

# Quality ordering for combining rating factors (lower index = better).
_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
_INV = {v: k for k, v in _ORDER.items()}

_TIN_BASE = {
    "fija": S.TIN_BASE_FIJA,
    "variable": S.TIN_BASE_VARIABLE,
    "mixta": S.TIN_BASE_MIXTA,
}


# ─────────────────────────── §3.4 Cuota ───────────────────────────
def cuota_mensual(principal: float, tin_pct: float, years: int) -> float:
    """Monthly payment (French amortization)."""
    return _calc_mortgage(principal, tin_pct, years)[0]


# ─────────────────────────── §3.2 LTV ─────────────────────────────
@dataclass
class LTVResult:
    ltv_pct: float
    entrada: float          # down payment required
    banda: str              # estándar / elevada / muy elevada / excepcional
    financiable: bool       # False if LTV > LTV_MAX_FINANCIABLE
    letra: str              # rating factor A/B/C/D


def calcular_ltv(
    importe_financiar: float,
    valor_tasacion: float,
    precio_compra: Optional[float] = None,
) -> LTVResult:
    """LTV = importe / min(tasación, compra). §3.2."""
    base = min(valor_tasacion, precio_compra) if precio_compra else valor_tasacion
    if base <= 0:
        raise ValueError("El valor de tasación/compra debe ser mayor que 0.")
    ltv = importe_financiar / base * 100
    entrada = max(base - importe_financiar, 0.0)

    if ltv <= 80:
        banda, letra = "estándar", "A"
    elif ltv <= 90:
        banda, letra = "elevada", "B"
    elif ltv <= 95:
        banda, letra = "muy elevada", "C"
    else:
        banda, letra = "excepcional", "D"

    return LTVResult(
        ltv_pct=round(ltv, 2),
        entrada=round(entrada, 2),
        banda=banda,
        financiable=ltv <= S.LTV_MAX_FINANCIABLE,
        letra=letra,
    )


# ─────────────────────────── §3.3 TIN final ───────────────────────
@dataclass
class TINResult:
    tin_base: float
    total_bonificacion: float    # pp subtracted
    ajuste_ltv: float            # pp added
    tin_final: float
    suelo_aplicado: bool         # True if floored at TIN_FLOOR
    derivar_excepcional: bool    # True if LTV > 95 (no automatic pricing)
    bonificaciones: dict         # {producto: pp}


def _bonificaciones_pp(
    nomina: bool,
    nomina_importe_mensual: float,
    seguro_hogar: bool,
    seguro_vida: bool,
    plan_pensiones: bool,
    plan_aportacion_anual: float,
) -> tuple[float, dict]:
    applied: dict = {}
    if nomina and nomina_importe_mensual >= S.NOMINA_MIN_MENSUAL:
        applied["nomina"] = S.BONIF_NOMINA
    if seguro_hogar:
        applied["seguro_hogar"] = S.BONIF_SEGURO_HOGAR
    if seguro_vida:
        applied["seguro_vida"] = S.BONIF_SEGURO_VIDA
    if plan_pensiones and plan_aportacion_anual >= S.PLAN_PENSIONES_MIN_ANUAL:
        applied["plan_pensiones"] = S.BONIF_PLAN_PENSIONES
    return round(sum(applied.values()), 4), applied


def _ajuste_ltv(ltv_pct: float) -> Optional[float]:
    """pp added to TIN for high LTV. Returns None if LTV > 95 (derive)."""
    if ltv_pct <= 80:
        return 0.0
    if ltv_pct <= 90:
        return S.LTV_PENALTY_80_90
    if ltv_pct <= 95:
        return S.LTV_PENALTY_90_95
    return None


def calcular_tin_final(
    producto: str,
    ltv_pct: float,
    *,
    nomina: bool = False,
    nomina_importe_mensual: float = 0.0,
    seguro_hogar: bool = False,
    seguro_vida: bool = False,
    plan_pensiones: bool = False,
    plan_aportacion_anual: float = 0.0,
) -> TINResult:
    """TIN_final = TIN_base − Σbonificaciones + ajuste_LTV, suelo TIN_FLOOR. §3.3."""
    producto = producto.lower()
    if producto not in _TIN_BASE:
        raise ValueError(f"Producto no reconocido: {producto!r}. Use fija/variable/mixta.")
    base = _TIN_BASE[producto]

    total_bonif, applied = _bonificaciones_pp(
        nomina, nomina_importe_mensual, seguro_hogar, seguro_vida,
        plan_pensiones, plan_aportacion_anual,
    )
    ajuste = _ajuste_ltv(ltv_pct)
    derivar = ajuste is None
    ajuste = ajuste or 0.0

    tin = base - total_bonif + ajuste
    suelo = tin < S.TIN_FLOOR
    if suelo:
        tin = S.TIN_FLOOR

    return TINResult(
        tin_base=base,
        total_bonificacion=total_bonif,
        ajuste_ltv=ajuste,
        tin_final=round(tin, 4),
        suelo_aplicado=suelo,
        derivar_excepcional=derivar,
        bonificaciones=applied,
    )


# ─────────────────────────── §4.2 Esfuerzo ────────────────────────
@dataclass
class EsfuerzoResult:
    ratio: float            # 0..1
    banda: str              # óptimo / aceptable / gris / alto
    letra: str


def calcular_esfuerzo(
    cuota: float, deudas_mensuales: float, ingresos_netos: float
) -> EsfuerzoResult:
    """Ratio_esfuerzo = (cuota + deudas) / ingresos. §4.2."""
    if ingresos_netos <= 0:
        raise ValueError("Los ingresos netos deben ser mayores que 0.")
    ratio = (cuota + deudas_mensuales) / ingresos_netos
    if ratio <= S.ESFUERZO_OPTIMO:
        banda, letra = "óptimo", "A"
    elif ratio <= S.ESFUERZO_ACEPTABLE:
        banda, letra = "aceptable", "B"
    elif ratio <= S.ESFUERZO_GRIS:
        banda, letra = "gris", "C"
    else:
        banda, letra = "alto", "D"
    return EsfuerzoResult(ratio=round(ratio, 4), banda=banda, letra=letra)


# ─────────────────────────── §4.3 Estabilidad ─────────────────────
@dataclass
class EstabilidadResult:
    nivel: str              # alta / media / baja
    letra: str


def calcular_estabilidad(
    contrato: str, antiguedad_anios: float, autonomo_estable: bool = True
) -> EstabilidadResult:
    """Job-stability level. §4.3. Unknown contracts fall back to conservative 'baja'."""
    c = contrato.lower().strip()
    if c == "funcionario":
        return EstabilidadResult("alta", "A")
    if c == "indefinido":
        return EstabilidadResult("alta", "A") if antiguedad_anios > 2 else EstabilidadResult("media", "B")
    if c in ("autonomo", "autónomo"):
        if antiguedad_anios > 2 and autonomo_estable:
            return EstabilidadResult("media", "B")
        return EstabilidadResult("baja", "C")
    if c == "temporal":
        return EstabilidadResult("baja", "C")
    return EstabilidadResult("baja", "C")


# ─────────────────────────── §4.4 Historial ───────────────────────
@dataclass
class HistorialResult:
    impagos_activos: bool
    revolving_intensivo: bool
    sin_historial: bool
    flag_revision: bool      # impagos → mandatory human review
    downgrade_niveles: int   # revolving → 1 level down
    letra: str               # impagos → D, else neutral A
    notas: list = field(default_factory=list)


def evaluar_historial(
    impagos_activos: bool = False,
    revolving_intensivo: bool = False,
    sin_historial: bool = False,
) -> HistorialResult:
    """Credit-history signals. §4.4. 'sin historial' is NOT penalized as risk."""
    notas = []
    if impagos_activos:
        notas.append("Impagos activos/recientes (< 2 años): riesgo alto y revisión humana obligatoria.")
    if revolving_intensivo:
        notas.append("Uso intensivo de revolving/microcréditos: -1 nivel de clasificación.")
    if sin_historial:
        notas.append("Historial no disponible: pendiente de verificación documental (no penaliza como impago).")
    return HistorialResult(
        impagos_activos=impagos_activos,
        revolving_intensivo=revolving_intensivo,
        sin_historial=sin_historial,
        flag_revision=impagos_activos,
        downgrade_niveles=1 if revolving_intensivo else 0,
        letra="D" if impagos_activos else "A",
        notas=notas,
    )


# ─────────────────────────── §4.5 Test de estrés ──────────────────
@dataclass
class StressResult:
    ratio_escenario_a: float   # TIN + 1 pp
    ratio_escenario_b: float   # ingresos × 0.80
    vulnerabilidad: bool       # any scenario > 45 %


def test_estres(
    principal: float, tin_final: float, years: int,
    deudas_mensuales: float, ingresos_netos: float,
) -> StressResult:
    """Two adverse scenarios; flags 'vulnerabilidad ante shocks'. §4.5."""
    if ingresos_netos <= 0:
        raise ValueError("Los ingresos netos deben ser mayores que 0.")
    cuota_a = cuota_mensual(principal, tin_final + S.STRESS_TIN_DELTA, years)
    ratio_a = (cuota_a + deudas_mensuales) / ingresos_netos

    cuota_base = cuota_mensual(principal, tin_final, years)
    ratio_b = (cuota_base + deudas_mensuales) / (ingresos_netos * S.STRESS_INCOME_FACTOR)

    vuln = ratio_a > S.STRESS_ESFUERZO_FLAG or ratio_b > S.STRESS_ESFUERZO_FLAG
    return StressResult(round(ratio_a, 4), round(ratio_b, 4), vuln)


# ─────────────────────────── §4.6 Rating ──────────────────────────
@dataclass
class RatingResult:
    factores: dict           # {esfuerzo, ltv, estabilidad, historial, vulnerabilidad} -> letter
    rating_base: str         # worst factor before adjustments
    rating_global: str
    regla_oro_aplicada: bool
    flag_revision_humana: bool
    notas: list


def calcular_rating(
    esfuerzo_letra: str,
    ltv_letra: str,
    estabilidad_letra: str,
    historial: HistorialResult,
    vulnerabilidad: bool,
    avalista: bool = False,
) -> RatingResult:
    """
    Combine factors. §4.6. Global rating = worst factor band, then:
      - revolving: one level down
      - regla de oro: a factor in D forces global no better than C; an avalista /
        second holder can lift a D back up to C (max).
    """
    factores = {
        "esfuerzo": esfuerzo_letra,
        "ltv": ltv_letra,
        "estabilidad": estabilidad_letra,
        "historial": historial.letra,
        "vulnerabilidad": "C" if vulnerabilidad else "A",
    }
    notas = list(historial.notas)
    if vulnerabilidad:
        notas.append("Vulnerabilidad ante shocks detectada en el test de estrés (factor negativo).")

    worst = _INV[max(_ORDER[v] for v in factores.values())]
    global_idx = _ORDER[worst]

    # revolving downgrade
    if historial.downgrade_niveles:
        global_idx = min(global_idx + historial.downgrade_niveles, 3)

    global_letter = _INV[global_idx]

    # regla de oro: D compensable by avalista up to C
    regla = False
    if global_letter == "D" and avalista:
        global_letter = "C"
        regla = True
        notas.append("Regla de oro: factor en D compensado por avalista/segundo titular → C.")

    # §7: rating C always derives; impagos always derive
    flag = global_letter == "C" or historial.flag_revision

    return RatingResult(
        factores=factores,
        rating_base=worst,
        rating_global=global_letter,
        regla_oro_aplicada=regla,
        flag_revision_humana=flag,
        notas=notas,
    )


# ─────────────────────────── §5 Rentabilidad ──────────────────────
@dataclass
class RentabilidadResult:
    margen_directo: float
    valor_vinculaciones_total: float
    rentabilidad_estimada: float
    clasificacion: str       # alta / media / baja


def calcular_rentabilidad(
    tin_final: float,
    principal: float,
    years: int,
    rating_global: str,
    bonificaciones: dict,
    euribor: Optional[float] = None,
) -> RentabilidadResult:
    """
    Internal profitability estimate. §5. Rates are percentages, divided by 100 to
    yield euros. The spec's classification table is fuzzy; mapped pragmatically:
    rating C/D → baja; no vinculaciones → media; otherwise positive A/B → alta.
    """
    euribor = S.EURIBOR_ACTUAL if euribor is None else euribor
    coste = euribor + S.COSTE_FONDOS_SPREAD
    margen_directo = (tin_final - coste) / 100 * principal * years

    valor_anual = sum(
        S.VALOR_VINC_ANUAL[k]
        for k, active in bonificaciones.items()
        if active and k in S.VALOR_VINC_ANUAL
    )
    factor = S.FACTOR_RIESGO.get(rating_global, 0.5)
    rentabilidad = margen_directo + (valor_anual * years) * factor

    if rating_global in ("C", "D"):
        clasificacion = "baja"
    elif valor_anual == 0:
        clasificacion = "media"
    elif rentabilidad > 0:
        clasificacion = "alta"
    else:
        clasificacion = "media"

    return RentabilidadResult(
        margen_directo=round(margen_directo, 2),
        valor_vinculaciones_total=round(valor_anual * years, 2),
        rentabilidad_estimada=round(rentabilidad, 2),
        clasificacion=clasificacion,
    )
