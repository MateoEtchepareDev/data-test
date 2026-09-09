from flask import Blueprint

from api.queries import kpis_sql
from api.routes import _num, _periodo_filtro, api_error_handler
from shared.db import connect

bp = Blueprint("kpis", __name__, url_prefix="/kpis")


@bp.get("/ventas-totales")
@api_error_handler
def ventas_totales():
    filtro = _periodo_filtro()
    with connect() as conn:
        total = kpis_sql.ventas_totales(conn, filtro)
    return {"ventas_totales": _num(total)}


@bp.get("/cantidad-vendida")
@api_error_handler
def cantidad_vendida():
    filtro = _periodo_filtro()
    with connect() as conn:
        cantidad = kpis_sql.cantidad_vendida(conn, filtro)
    return {"cantidad_vendida": _num(cantidad)}


@bp.get("/ticket-promedio")
@api_error_handler
def ticket_promedio():
    filtro = _periodo_filtro()
    with connect() as conn:
        rows = kpis_sql.ticket_promedio(conn, filtro)
    return [
        {
            "id_sucursal": row["id_sucursal"],
            "nombre_sucursal": row["nombre_sucursal"],
            "ticket_promedio": _num(row["ticket_promedio"]),
        }
        for row in rows
    ]


@bp.get("/margen-bruto")
@api_error_handler
def margen_bruto():
    filtro = _periodo_filtro()
    with connect() as conn:
        margen = kpis_sql.margen_bruto(conn, filtro)
    return {"margen_bruto": _num(margen)}