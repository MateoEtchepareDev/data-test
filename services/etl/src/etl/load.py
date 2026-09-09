from psycopg2.extras import execute_values

from shared.db import connect
from shared.schema import (
    TABLE_DIM_PRODUCTO,
    TABLE_DIM_PROVINCIA,
    TABLE_DIM_SUCURSAL,
    TABLE_DIM_TIEMPO,
    TABLE_FACT_VENTAS,
)

ORDER = [
    TABLE_DIM_PROVINCIA,
    TABLE_DIM_TIEMPO,
    TABLE_DIM_PRODUCTO,
    TABLE_DIM_SUCURSAL,
    TABLE_FACT_VENTAS,
]


def _to_rows(df, columns):
    return [tuple(row) for row in df[columns].astype(object).to_numpy().tolist()]


def _upsert(conn, table, columns, rows, conflict_col):
    if not rows:
        return 0
    assignments = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns)
    insert = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s "
        f"ON CONFLICT ({conflict_col}) DO UPDATE SET {assignments}"
    )
    with conn.cursor() as cur:
        execute_values(cur, insert, rows)
    return len(rows)


def load(data):
    specs = {
        TABLE_DIM_PROVINCIA: (["id_provincia", "nombre_provincia"], "id_provincia"),
        TABLE_DIM_TIEMPO: (["fecha", "anio", "trimestre", "mes"], "fecha"),
        TABLE_DIM_PRODUCTO: (
            ["id_producto", "nombre_producto", "categoria", "costo"],
            "id_producto",
        ),
        TABLE_DIM_SUCURSAL: (
            ["id_sucursal", "nombre_sucursal", "id_provincia"],
            "id_sucursal",
        ),
        TABLE_FACT_VENTAS: (
            ["id_ticket", "fecha", "id_sucursal", "id_producto", "cantidad", "precio_unitario"],
            "id_ticket",
        ),
    }
    counts = {}
    with connect() as conn:
        for table in ORDER:
            columns, conflict_col = specs[table]
            counts[table] = _upsert(conn, table, columns, _to_rows(data[table], columns), conflict_col)
        conn.commit()
    return counts