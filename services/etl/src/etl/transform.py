import pandas as pd

from etl.validate import (
    PROVINCIA_MAP,
    SHEET_HECHOS,
    SHEET_PRODUCTO,
    SHEET_SUCURSAL,
    SHEET_TIEMPO,
    ContractError,
)


def normalize_provincia(provincia):
    if provincia not in PROVINCIA_MAP:
        raise ContractError(f"{SHEET_SUCURSAL}.provincia: valor fuera del mapa: {provincia}")
    return PROVINCIA_MAP[provincia]


def _trimestre(mes):
    return (mes - 1) // 3 + 1


def transform(frames):
    t = frames[SHEET_TIEMPO]
    for _, row in t.iterrows():
        fecha = row["fecha"]
        if fecha.year != row["anio"] or fecha.month != row["mes"] or _trimestre(fecha.month) != row["trimestre"]:
            raise ContractError(
                f"{SHEET_TIEMPO}: derivaciones inconsistentes para id_fecha {row['id_fecha']} "
                f"(fecha={fecha.date()}, esperado anio/trimestre/mes={fecha.year}/"
                f"{_trimestre(fecha.month)}/{fecha.month}, hay anio/trimestre/mes={row['anio']}/"
                f"{row['trimestre']}/{row['mes']})"
            )

    dim_tiempo = pd.DataFrame(
        {
            "fecha": pd.to_datetime(t["fecha"]).dt.date,
            "anio": t["anio"],
            "trimestre": t["trimestre"],
            "mes": t["mes"],
        }
    )

    p = frames[SHEET_PRODUCTO]
    dim_producto = p[["id_producto", "nombre", "categoria", "costo"]].rename(
        columns={"nombre": "nombre_producto"}
    )

    s = frames[SHEET_SUCURSAL]
    provincias = sorted({normalize_provincia(x) for x in s["provincia"].unique()})
    id_prov = {name: i + 1 for i, name in enumerate(provincias)}
    dim_provincia = pd.DataFrame(
        {"id_provincia": list(id_prov.values()), "nombre_provincia": list(id_prov.keys())}
    )
    dim_sucursal = s[["id_sucursal", "ciudad"]].rename(columns={"ciudad": "nombre_sucursal"})
    dim_sucursal["id_provincia"] = s["provincia"].map(normalize_provincia).map(id_prov)

    fecha_map = dict(zip(t["id_fecha"], pd.to_datetime(t["fecha"]).dt.date))
    h = frames[SHEET_HECHOS]
    fact_ventas = pd.DataFrame(
        {
            "id_ticket": h["nro_venta"],
            "fecha": h["id_fecha"].map(fecha_map),
            "id_sucursal": h["id_sucursal"],
            "id_producto": h["id_producto"],
            "cantidad": h["cantidad"],
            "precio_unitario": h["precio_unitario"],
        }
    )

    return {
        "dim_provincia": dim_provincia,
        "dim_producto": dim_producto,
        "dim_tiempo": dim_tiempo,
        "dim_sucursal": dim_sucursal,
        "fact_ventas": fact_ventas,
    }