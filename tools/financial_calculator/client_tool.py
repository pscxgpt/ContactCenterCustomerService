"""
ConsultarClienteTool — looks up an existing client by DNI or phone so the
mortgage agent can confirm their profile and skip asking for income, contract,
debts and linked products. The returned text also tells the LLM to evaluate
with `cliente_dni`, so the engine reads the financials authoritatively.
"""
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from tools.financial_calculator.client_lookup import ClientRecord, buscar_cliente


class ConsultarClienteInput(BaseModel):
    identificador: str = Field(..., description="DNI o número de teléfono del cliente.")


def _resumen(r: ClientRecord) -> str:
    productos = []
    if r.nomina:
        productos.append("nómina domiciliada")
    if r.seguro_hogar:
        productos.append("seguro de hogar")
    if r.seguro_vida:
        productos.append("seguro de vida")
    if r.plan_pensiones:
        productos.append("plan de pensiones")
    productos_txt = ", ".join(productos) if productos else "sin productos vinculados"
    deudas_txt = (
        f"{r.deudas_mensuales:,.0f} €/mes en deudas" if r.deudas_mensuales > 0
        else "sin deudas registradas"
    )
    return (
        f"CLIENTE LOCALIZADO: {r.nombre} (cliente desde {r.cliente_desde}).\n"
        f"- Ingresos netos: {r.ingresos_netos:,.0f} €/mes\n"
        f"- Contrato: {r.contrato} ({r.antiguedad_anios:g} años de antigüedad)\n"
        f"- Situación: {deudas_txt}\n"
        f"- Productos contratados: {productos_txt}\n\n"
        f"Confírmale estos datos en UNA frase (sin volver a preguntarlos) y NO le preguntes "
        f"por vinculaciones: ya constan en el sistema. Si el cliente AÚN no te ha dado los "
        f"datos de la vivienda (producto, importe, valor, plazo), pídeselos; si YA te los ha "
        f"dado, llama de inmediato a EvaluarHipotecaClienteTool con cliente_dni=\"{r.dni}\" y "
        f"esos 4 datos (sus datos financieros los toma el sistema, no los pases tú)."
    )


class ConsultarClienteTool(BaseTool):
    name: str = "ConsultarClienteTool"
    description: str = (
        "Busca a un cliente existente del banco por DNI o teléfono y devuelve su perfil "
        "financiero (ingresos, contrato, antigüedad, deudas y productos vinculados). "
        "Úsala cuando el cliente diga que YA es cliente del banco y te facilite su DNI o "
        "teléfono, para no tener que preguntarle esos datos."
    )
    args_schema: Type[BaseModel] = ConsultarClienteInput

    def _run(self, identificador: str) -> str:
        r = buscar_cliente(identificador)
        if r is None:
            return (
                "No encuentro ningún cliente con ese DNI o teléfono. Puedo seguir con la "
                "simulación pidiéndote los datos directamente."
            )
        return _resumen(r)
