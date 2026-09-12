from psycopg2.extras import RealDictCursor

from shared.schema import (
    TABLE_DIM_PRODUCTO,
    TABLE_DIM_PROVINCIA,
    TABLE_DIM_SUCURSAL,
    TABLE_DIM_TIEMPO,
    TABLE_FACT_VENTAS,
)


def top_productos(conn, anio=None, trimestre=None, limit=5):
    sql = (
        f"SELECT p.id_producto, p.nombre_producto, "
        f"SUM(fv.cantidad * fv.precio_unitario) AS ventas "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_PRODUCTO} AS p ON fv.id_producto = p.id_producto "
        f"JOIN {TABLE_DIM_TIEMPO} AS t ON fv.fecha = t.fecha "
        f"WHERE t.anio = %s AND t.trimestre = %s "
        f"GROUP BY p.id_producto, p.nombre_producto "
        f"ORDER BY ventas DESC "
        f"LIMIT %s"
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, (anio, trimestre, limit))
        return cur.fetchall()


def margen_por_categoria(conn):
    sql = (
        f"SELECT p.categoria, "
        f"SUM(fv.cantidad * (fv.precio_unitario - p.costo)) AS margen "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_PRODUCTO} AS p ON fv.id_producto = p.id_producto "
        f"GROUP BY p.categoria "
        f"ORDER BY margen DESC"
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql)
        return cur.fetchall()


def provincia_mayor_volumen(conn):
    sql = (
        f"SELECT pr.nombre_provincia AS provincia, "
        f"SUM(fv.cantidad * fv.precio_unitario) AS ventas "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_SUCURSAL} AS s ON fv.id_sucursal = s.id_sucursal "
        f"JOIN {TABLE_DIM_PROVINCIA} AS pr ON s.id_provincia = pr.id_provincia "
        f"GROUP BY pr.nombre_provincia "
        f"ORDER BY ventas DESC "
        f"LIMIT 1"
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql)
        return cur.fetchone()


def ventas_por_provincia(conn):
    sql = (
        f"SELECT pr.nombre_provincia AS provincia, "
        f"SUM(fv.cantidad * fv.precio_unitario) AS ventas "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_SUCURSAL} AS s ON fv.id_sucursal = s.id_sucursal "
        f"JOIN {TABLE_DIM_PROVINCIA} AS pr ON s.id_provincia = pr.id_provincia "
        f"GROUP BY pr.nombre_provincia "
        f"ORDER BY ventas DESC"
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql)
        return cur.fetchall()


def categoria_mas_rentable(conn):
    sql = (
        f"SELECT p.categoria, "
        f"SUM(fv.cantidad * (fv.precio_unitario - p.costo)) AS margen "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_PRODUCTO} AS p ON fv.id_producto = p.id_producto "
        f"GROUP BY p.categoria "
        f"ORDER BY margen DESC "
        f"LIMIT 1"
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql)
        return cur.fetchone()


def evolucion_mensual(conn):
    sql = (
        f"SELECT t.anio, t.mes, SUM(fv.cantidad * fv.precio_unitario) AS ventas "
        f"FROM {TABLE_FACT_VENTAS} AS fv "
        f"JOIN {TABLE_DIM_TIEMPO} AS t ON fv.fecha = t.fecha "
        f"GROUP BY t.anio, t.mes "
        f"ORDER BY t.anio, t.mes"
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql)
        return cur.fetchall()