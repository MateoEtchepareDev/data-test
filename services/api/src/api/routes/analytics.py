from flask import Blueprint

from api.queries import analytics_sql
from api.routes import _num, _periodo_filtro, api_error_handler
from shared.db import connect

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.get("/top-productos")
@api_error_handler
def top_productos():
    filtro = _periodo_filtro()
    anio = filtro.get("anio", 2024)
    trimestre = filtro.get("trimestre", 4)
    with connect() as conn:
        rows = analytics_sql.top_productos(conn, anio, trimestre, limit=5)
    return [
        {
            "id_producto": row["id_producto"],
            "nombre_producto": row["nombre_producto"],
            "ventas": _num(row["ventas"]),
        }
        for row in rows
    ]


@bp.get("/margen-por-categoria")
@api_error_handler
def margen_por_categoria():
    with connect() as conn:
        rows = analytics_sql.margen_por_categoria(conn)
    return [
        {"categoria": row["categoria"], "margen": _num(row["margen"])}
        for row in rows
    ]


@bp.get("/provincia-mayor-volumen")
@api_error_handler
def provincia_mayor_volumen():
    with connect() as conn:
        row = analytics_sql.provincia_mayor_volumen(conn)
    if not row:
        return {"provincia": None, "ventas": None}
    return {"provincia": row["provincia"], "ventas": _num(row["ventas"])}


@bp.get("/ventas-por-provincia")
@api_error_handler
def ventas_por_provincia():
    with connect() as conn:
        rows = analytics_sql.ventas_por_provincia(conn)
    return [
        {"provincia": row["provincia"], "ventas": _num(row["ventas"])}
        for row in rows
    ]


@bp.get("/categoria-mas-rentable")
@api_error_handler
def categoria_mas_rentable():
    with connect() as conn:
        row = analytics_sql.categoria_mas_rentable(conn)
    if not row:
        return {"categoria": None, "margen": None}
    return {"categoria": row["categoria"], "margen": _num(row["margen"])}


@bp.get("/evolucion-mensual")
@api_error_handler
def evolucion_mensual():
    with connect() as conn:
        rows = analytics_sql.evolucion_mensual(conn)
    return [
        {"anio": row["anio"], "mes": row["mes"], "ventas": _num(row["ventas"])}
        for row in rows
    ]