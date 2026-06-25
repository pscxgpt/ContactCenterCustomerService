"""
client_lookup.py — deterministic lookup of an existing bank client.

Reads the synthetic clients dataset and returns a client's financial profile so
the mortgage agent can pre-fill it instead of asking. Pure Python: the client's
authoritative data (income, contract, debts, products) is read here and fed
straight into the engine — it never has to be transcribed by the LLM.
"""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from config.settings import CLIENTES_CSV

_TRUE = {"si", "sí", "true", "1", "yes", "y", "s", "x"}


def _to_bool(v) -> bool:
    return str(v).strip().lower() in _TRUE


def _to_float(v) -> float:
    s = str(v).strip().replace(",", ".")
    return float(s) if s else 0.0


def _norm_dni(s) -> str:
    return re.sub(r"\s+", "", str(s)).upper()


def _digits(s) -> str:
    return re.sub(r"\D", "", str(s))


@dataclass
class ClientRecord:
    dni: str
    nombre: str
    telefono: str
    ingresos_netos: float
    contrato: str
    antiguedad_anios: float
    deudas_mensuales: float
    nomina: bool
    nomina_importe_mensual: float
    seguro_hogar: bool
    seguro_vida: bool
    plan_pensiones: bool
    plan_aportacion_anual: float
    impagos_activos: bool
    autonomo_estable: bool
    cliente_desde: str

    def to_profile_fields(self) -> dict:
        """The MortgageProfile/EvaluarHipotecaTool fields known from the bank's
        records. Property- and preference-specific fields (producto, importe,
        valor, plazo) are NOT here — those still come from the conversation."""
        return dict(
            ingresos_netos=self.ingresos_netos,
            contrato=self.contrato,
            antiguedad_anios=self.antiguedad_anios,
            deudas_mensuales=self.deudas_mensuales,
            nomina=self.nomina,
            nomina_importe_mensual=self.nomina_importe_mensual,
            seguro_hogar=self.seguro_hogar,
            seguro_vida=self.seguro_vida,
            plan_pensiones=self.plan_pensiones,
            plan_aportacion_anual=self.plan_aportacion_anual,
            impagos_activos=self.impagos_activos,
            autonomo_estable=self.autonomo_estable,
        )


@lru_cache(maxsize=1)
def _load() -> list[ClientRecord]:
    if not os.path.exists(CLIENTES_CSV):
        return []
    records: list[ClientRecord] = []
    with open(CLIENTES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            autonomo = row.get("autonomo_estable", "")
            records.append(
                ClientRecord(
                    dni=_norm_dni(row.get("dni", "")),
                    nombre=row.get("nombre", "").strip(),
                    telefono=row.get("telefono", "").strip(),
                    ingresos_netos=_to_float(row.get("ingresos_netos")),
                    contrato=row.get("contrato", "indefinido").strip().lower(),
                    antiguedad_anios=_to_float(row.get("antiguedad_anios")),
                    deudas_mensuales=_to_float(row.get("deudas_mensuales")),
                    nomina=_to_bool(row.get("nomina")),
                    nomina_importe_mensual=_to_float(row.get("nomina_importe_mensual")),
                    seguro_hogar=_to_bool(row.get("seguro_hogar")),
                    seguro_vida=_to_bool(row.get("seguro_vida")),
                    plan_pensiones=_to_bool(row.get("plan_pensiones")),
                    plan_aportacion_anual=_to_float(row.get("plan_aportacion_anual")),
                    impagos_activos=_to_bool(row.get("impagos_activos")),
                    # default True when the column is blank (only meaningful for autónomos)
                    autonomo_estable=_to_bool(autonomo) if str(autonomo).strip() else True,
                    cliente_desde=str(row.get("cliente_desde", "")).strip(),
                )
            )
    return records


def buscar_cliente(identificador: str) -> Optional[ClientRecord]:
    """Find a client by DNI (case/space-insensitive) or phone (last 9 digits)."""
    if not identificador:
        return None
    dni = _norm_dni(identificador)
    phone = _digits(identificador)
    for r in _load():
        if dni and r.dni == dni:
            return r
        if len(phone) >= 9 and _digits(r.telefono).endswith(phone[-9:]):
            return r
    return None
