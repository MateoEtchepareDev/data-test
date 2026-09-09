from psycopg2.extras import RealDictCursor

from shared.schema import (
    TABLE_DIM_PRODUCTO,
    TABLE_DIM_SUCURSAL,
    TABLE_DIM_TIEMPO,
    TABLE_FACT_VENTAS,
)

PERIODO_COLS = ("anio", "trimestre", "mes")


def _filtro_sql(filtro):
    conds = []
    params = []
    for name in PERIODO_COLS:
        if name in filtro:
            conds.append(f"t.{name} = %s")
            params.append(filtro[name])
    if not conds:
        return "", "", ()
    join = f" JOIN {TABLE_DIM_TIEMPO} AS t ON fv.fecha = t.fecha"
    where = " WHERE " + " AND ".join(conds)
    return join, where, tuple(params)


def ventas_totales(conn, filtro=None):
    filtro = filtro or {}
    join, where, params = _filtro_sql(filtro)
    sql = (
        f"SELECT COALESCE(SUM(fv.cantidad * fv.precio_unitario), 0) "
        f"FROM {TABLE_FACT_VENTAS} AS fv{join}{where}"
    )
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


def cantidad_vendida(conn, filtro=None):
    filtro = filtro or {}
    join, where, params = _filtro_sql(filtro)
    sql = (
        f"SELECT COALESCE(SUM(fv.cantidad), 0) "
        f"FROM {TABLE_FACT_VENTAS} AS fv{join}{where}"
    )
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


def ticket_promedio(conn, filtro=None):
    filtro = filtro or {}
    join, where, params = _filtro_sql(filtro)
    sql = (
        f"SELECT s.id_sucursal AS id_sucursal, s.nombre_sucursal AS nombre_sucursal, "
        f"SUM(fv.cantidad * fv.precio_unitario) / COUNT(*) AS ticket_promedio "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_SUCURSAL} AS s ON fv.id_sucursal = s.id_sucursal{join}{where} "
        f"GROUP BY s.id_sucursal, s.nombre_sucursal "
        f"ORDER BY s.id_sucursal"
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def margen_bruto(conn, filtro=None):
    filtro = filtro or {}
    join, where, params = _filtro_sql(filtro)
    sql = (
        f"SELECT COALESCE(SUM(fv.cantidad * (fv.precio_unitario - p.costo)), 0) "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_PRODUCTO} AS p ON fv.id_producto = p.id_producto{join}{where}"
    )
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]