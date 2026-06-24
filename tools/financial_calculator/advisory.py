"""
advisory.py — Deterministic advisory engine for the mortgage agent.

Given a complete MortgageProfile, runs the spec's three phases and returns a
structured AdvisoryResult plus a §8-safe client message. Pure Python: the LLM
later only extracts the profile from the conversation and rephrases the message;
every decision here is deterministic and unit-tested.

Spec: agente_hipotecas_system_prompt.md §3–§7.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from tools.financial_calculator import mortgage_core as mc

# §6.1 decision tree: rating → action
DECISION = {
    "A": "ofertar",
    "B": "ofertar_validacion",
    "C": "zona_gris_derivar",
    "D": "no_viable",
}


@dataclass
class MortgageProfile:
    # Fase 1 (required)
    producto: str                      # fija / variable / mixta
    importe_financiar: float
    valor_tasacion: float
    plazo_anios: int
    # Fase 2 (required)
    ingresos_netos: float
    contrato: str = "indefinido"
    antiguedad_anios: float = 0.0
    deudas_mensuales: float = 0.0
    # Optional context
    precio_compra: Optional[float] = None
    autonomo_estable: bool = True
    impagos_activos: bool = False
    revolving_intensivo: bool = False
    sin_historial: bool = False
    avalista: bool = False
    # Vinculaciones
    nomina: bool = False
    nomina_importe_mensual: float = 0.0
    seguro_hogar: bool = False
    seguro_vida: bool = False
    plan_pensiones: bool = False
    plan_aportacion_anual: float = 0.0
    # Escalation triggers (§7)
    vivienda_habitual: bool = True
    caso_no_estandar: bool = False
    solicita_humano: bool = False


@dataclass
class Recomendacion:
    tipo: str       # modificar / contratar / eliminar
    titulo: str
    efecto: str


@dataclass
class AdvisoryResult:
    ltv: mc.LTVResult
    tin: mc.TINResult
    cuota: float
    esfuerzo: mc.EsfuerzoResult
    estabilidad: mc.EstabilidadResult
    historial: mc.HistorialResult
    stress: mc.StressResult
    rating: mc.RatingResult
    rentabilidad: mc.RentabilidadResult
    decision: str
    escalar_humano: bool
    motivos_escalado: list
    recomendaciones: list
    avisos: list


# ── Bonification helpers ───────────────────────────────────────────
_BONIF_KEYS = ("nomina", "seguro_hogar", "seguro_vida", "plan_pensiones")


def _bonif_kwargs(p: MortgageProfile) -> dict:
    return dict(
        nomina=p.nomina,
        nomina_importe_mensual=p.nomina_importe_mensual,
        seguro_hogar=p.seguro_hogar,
        seguro_vida=p.seguro_vida,
        plan_pensiones=p.plan_pensiones,
        plan_aportacion_anual=p.plan_aportacion_anual,
    )


def _bonif_active(p: MortgageProfile) -> dict:
    """Which vinculaciones are effectively active (thresholds met)."""
    from config import settings as S
    return {
        "nomina": p.nomina and p.nomina_importe_mensual >= S.NOMINA_MIN_MENSUAL,
        "seguro_hogar": p.seguro_hogar,
        "seguro_vida": p.seguro_vida,
        "plan_pensiones": p.plan_pensiones and p.plan_aportacion_anual >= S.PLAN_PENSIONES_MIN_ANUAL,
    }


def _bonif_disponibles(p: MortgageProfile) -> list:
    active = _bonif_active(p)
    return [k for k in _BONIF_KEYS if not active[k]]


def _bonif_kwargs_all(p: MortgageProfile) -> dict:
    """Bonification kwargs with every product enabled at threshold (max discount sim)."""
    from config import settings as S
    return dict(
        nomina=True, nomina_importe_mensual=max(p.nomina_importe_mensual, S.NOMINA_MIN_MENSUAL),
        seguro_hogar=True, seguro_vida=True,
        plan_pensiones=True, plan_aportacion_anual=max(p.plan_aportacion_anual, S.PLAN_PENSIONES_MIN_ANUAL),
    )


# ── §6.3 Recommendation engine ─────────────────────────────────────
def _generar_recomendaciones(
    p: MortgageProfile, ltv, tin, cuota, esfuerzo, rating, rentabilidad
) -> list:
    disponibles = _bonif_disponibles(p)

    # Rating A: only nudge vinculaciones when profitability isn't high (§6.2)
    if rating.rating_global == "A":
        if rentabilidad.clasificacion != "alta" and disponibles:
            return [Recomendacion(
                "contratar", "Añadir alguna vinculación",
                "Mejora el tipo de interés sin coste extra relevante.",
            )]
        return []

    # Rating B/C/D: evaluate levers and rank by how much they cut the esfuerzo ratio
    candidatas: list[tuple[float, Recomendacion]] = []

    # MODIFICAR — alargar plazo a 30 años
    if p.plazo_anios < 30:
        nc = mc.cuota_mensual(p.importe_financiar, tin.tin_final, 30)
        ne = mc.calcular_esfuerzo(nc, p.deudas_mensuales, p.ingresos_netos)
        candidatas.append((esfuerzo.ratio - ne.ratio, Recomendacion(
            "modificar", "Ampliar el plazo a 30 años",
            f"La cuota baja de {cuota:,.0f} € a {nc:,.0f} €/mes (aumentan los intereses totales).",
        )))

    # CONTRATAR — vinculaciones disponibles
    if disponibles:
        tin2 = mc.calcular_tin_final(p.producto, ltv.ltv_pct, **_bonif_kwargs_all(p))
        nc = mc.cuota_mensual(p.importe_financiar, tin2.tin_final, p.plazo_anios)
        ne = mc.calcular_esfuerzo(nc, p.deudas_mensuales, p.ingresos_netos)
        candidatas.append((esfuerzo.ratio - ne.ratio, Recomendacion(
            "contratar", "Contratar vinculaciones (nómina, seguros)",
            f"El tipo bajaría a {tin2.tin_final:.2f}% y la cuota a {nc:,.0f} €/mes.",
        )))

    # CONTRATAR — avalista cuando el riesgo es alto
    if rating.rating_global == "D" and not p.avalista:
        candidatas.append((0.0, Recomendacion(
            "contratar", "Añadir un avalista o segundo titular",
            "Permite reestudiar el caso combinando ambos perfiles.",
        )))

    # ELIMINAR — cancelar deudas existentes
    if p.deudas_mensuales > 0:
        ne = mc.calcular_esfuerzo(cuota, 0.0, p.ingresos_netos)
        candidatas.append((esfuerzo.ratio - ne.ratio, Recomendacion(
            "eliminar", "Cancelar deudas pequeñas antes de formalizar",
            "Reduce el esfuerzo mensual y mejora la viabilidad de la operación.",
        )))

    candidatas.sort(key=lambda t: t[0], reverse=True)
    return [r for _, r in candidatas[:3]]   # §6.3: máximo 2-3 alternativas


# ── Main entry point ───────────────────────────────────────────────
def evaluar_hipoteca(p: MortgageProfile) -> AdvisoryResult:
    # ── Fase 1: Cálculo ──
    ltv = mc.calcular_ltv(p.importe_financiar, p.valor_tasacion, p.precio_compra)
    tin = mc.calcular_tin_final(p.producto, ltv.ltv_pct, **_bonif_kwargs(p))
    cuota = mc.cuota_mensual(p.importe_financiar, tin.tin_final, p.plazo_anios)

    # ── Fase 2: Análisis de riesgo ──
    esfuerzo = mc.calcular_esfuerzo(cuota, p.deudas_mensuales, p.ingresos_netos)
    estabilidad = mc.calcular_estabilidad(p.contrato, p.antiguedad_anios, p.autonomo_estable)
    historial = mc.evaluar_historial(p.impagos_activos, p.revolving_intensivo, p.sin_historial)
    stress = mc.test_estres(p.importe_financiar, tin.tin_final, p.plazo_anios,
                            p.deudas_mensuales, p.ingresos_netos)
    rating = mc.calcular_rating(esfuerzo.letra, ltv.letra, estabilidad.letra,
                                historial, stress.vulnerabilidad, p.avalista)

    # ── Capa intermedia: rentabilidad ──
    rentabilidad = mc.calcular_rentabilidad(
        tin.tin_final, p.importe_financiar, p.plazo_anios,
        rating.rating_global, _bonif_active(p),
    )

    # ── Fase 3: decisión + escalado (§6.1, §7) ──
    decision = DECISION[rating.rating_global]

    motivos = []
    if rating.rating_global == "C":
        motivos.append("Rating en zona gris: revisión humana obligatoria.")
    if p.impagos_activos:
        motivos.append("Impagos activos declarados por el cliente.")
    if not ltv.financiable:
        motivos.append("LTV superior al 95 %: financiación excepcional.")
    if p.caso_no_estandar:
        motivos.append("Caso fuera de las reglas estándar (herencia, extranjero, etc.).")
    if not p.vivienda_habitual:
        motivos.append("Vivienda no habitual: condiciones especiales.")
    if p.solicita_humano:
        motivos.append("El cliente solicita hablar con un gestor humano.")
    escalar = bool(motivos)

    avisos = []
    if not ltv.financiable:
        avisos.append("La financiación supera el 95 % del valor; no es habitual salvo casos excepcionales.")
    if tin.suelo_aplicado:
        avisos.append("Se ha aplicado el tipo mínimo disponible.")
    if not p.vivienda_habitual:
        avisos.append("Para vivienda no habitual, las condiciones estándar pueden no aplicar.")

    recomendaciones = _generar_recomendaciones(
        p, ltv, tin, cuota, esfuerzo, rating, rentabilidad
    )

    return AdvisoryResult(
        ltv=ltv, tin=tin, cuota=round(cuota, 2),
        esfuerzo=esfuerzo, estabilidad=estabilidad, historial=historial,
        stress=stress, rating=rating, rentabilidad=rentabilidad,
        decision=decision, escalar_humano=escalar, motivos_escalado=motivos,
        recomendaciones=recomendaciones, avisos=avisos,
    )


# ── §8-safe client message (no internal rating/score/formulas) ─────
_VERDICTO = {
    "ofertar": "Con los datos que me has facilitado, tu operación encaja bien con nuestras condiciones.",
    "ofertar_validacion": "Tu operación es viable, aunque quedaría sujeta a una validación adicional por nuestra parte.",
    "zona_gris_derivar": "Tu caso está en un punto que prefiero que revise un gestor para darte una respuesta definitiva.",
    "no_viable": "Con los datos actuales, no podríamos seguir adelante con la operación tal y como está planteada.",
}


def render_mensaje_cliente(r: AdvisoryResult) -> str:
    """Plain-text, §8-safe summary for the customer (no A/B/C/D, no formulas)."""
    lines = ["Resumen de tu simulación (estimación orientativa):"]
    lines.append(f"  - Tipo de interés estimado (TIN): {r.tin.tin_final:.2f}%")
    lines.append(f"  - Cuota mensual aproximada: {r.cuota:,.2f} €")
    lines.append(f"  - LTV (financiación sobre el valor): {r.ltv.ltv_pct:.1f}%")
    lines.append("")
    lines.append(_VERDICTO[r.decision])

    for aviso in r.avisos:
        lines.append(f"  · {aviso}")

    if r.recomendaciones:
        lines.append("")
        lines.append("Algunas opciones para mejorar tu propuesta:")
        for rec in r.recomendaciones:
            lines.append(f"  - {rec.titulo}: {rec.efecto}")

    if r.escalar_humano:
        lines.append("")
        lines.append("Voy a pasar tu caso a un gestor humano para que lo revise y te dé una respuesta final.")

    lines.append("")
    lines.append("Recuerda que es una estimación orientativa, sujeta a validación posterior por el banco.")
    return "\n".join(lines)


def render_resumen_interno(r: AdvisoryResult) -> str:
    """Internal handoff summary (includes rating/scoring) — NOT for the client."""
    lines = [
        "=== RESUMEN INTERNO (no comunicar al cliente) ===",
        f"Decisión: {r.decision}  |  Rating global: {r.rating.rating_global}",
        f"Factores: {r.rating.factores}",
        f"TIN final: {r.tin.tin_final:.2f}%  (base {r.tin.tin_base}%, "
        f"bonif -{r.tin.total_bonificacion}pp, LTV +{r.tin.ajuste_ltv}pp)",
        f"Cuota: {r.cuota:,.2f} €  |  Esfuerzo: {r.esfuerzo.ratio:.1%} ({r.esfuerzo.banda})",
        f"Estabilidad: {r.estabilidad.nivel}  |  Vulnerabilidad estrés: {r.stress.vulnerabilidad}",
        f"Rentabilidad: {r.rentabilidad.clasificacion} ({r.rentabilidad.rentabilidad_estimada:,.0f} €)",
    ]
    if r.rating.notas:
        lines.append("Notas: " + " ".join(r.rating.notas))
    if r.escalar_humano:
        lines.append("Escalado a humano: " + "; ".join(r.motivos_escalado))
    return "\n".join(lines)
