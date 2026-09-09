import pandas as pd
import pytest

from etl.transform import transform
from etl.validate import ContractError, SHEET_HECHOS, SHEET_PRODUCTO, SHEET_SUCURSAL, SHEET_TIEMPO


def _base_frames():
    return {
        SHEET_HECHOS: pd.DataFrame(
            [
                {
                    "nro_venta": 1,
                    "id_fecha": 1,
                    "id_producto": 1,
                    "id_sucursal": 1,
                    "cantidad": 2,
                    "precio_unitario": 10.0,
                    "total": 20.0,
                },
                {
                    "nro_venta": 2,
                    "id_fecha": 2,
                    "id_producto": 2,
                    "id_sucursal": 2,
                    "cantidad": 1,
                    "precio_unitario": 5.0,
                    "total": 5.0,
                },
            ]
        ),
        SHEET_PRODUCTO: pd.DataFrame(
            [
                {"id_producto": 1, "nombre": "Prod A", "categoria": "Cat1", "costo": 5.0},
                {"id_producto": 2, "nombre": "Prod B", "categoria": "Cat2", "costo": 2.0},
            ]
        ),
        SHEET_SUCURSAL: pd.DataFrame(
            [
                {"id_sucursal": 1, "ciudad": "C1", "provincia": "Buenos Aires", "tipo": "T1"},
                {"id_sucursal": 2, "ciudad": "C2", "provincia": "Córdoba", "tipo": "T2"},
            ]
        ),
        SHEET_TIEMPO: pd.DataFrame(
            [
                {"id_fecha": 1, "fecha": pd.Timestamp("2024-01-01"), "dia": 1, "mes": 1, "trimestre": 1, "anio": 2024},
                {"id_fecha": 2, "fecha": pd.Timestamp("2024-04-01"), "dia": 1, "mes": 4, "trimestre": 2, "anio": 2024},
            ]
        ),
    }


def test_transform_builds_dim_tiempo():
    data = transform(_base_frames())
    dt = data["dim_tiempo"]
    assert len(dt) == 2
    assert list(dt.columns) == ["fecha", "anio", "trimestre", "mes"]
    assert dt.iloc[0]["trimestre"] == 1
    assert dt.iloc[1]["trimestre"] == 2


def test_transform_builds_dim_producto():
    data = transform(_base_frames())
    dp = data["dim_producto"]
    assert len(dp) == 2
    assert list(dp.columns) == ["id_producto", "nombre_producto", "categoria", "costo"]


def test_transform_normalizes_provincia_and_builds_dims():
    data = transform(_base_frames())
    prov = data["dim_provincia"]
    suc = data["dim_sucursal"]
    assert list(prov.columns) == ["id_provincia", "nombre_provincia"]
    assert set(prov["nombre_provincia"]) == {"Buenos Aires", "Córdoba"}
    assert len(suc) == 2
    assert suc["id_provincia"].isin(prov["id_provincia"]).all()


def test_transform_fact_ventas_uses_fecha_map():
    data = transform(_base_frames())
    fv = data["fact_ventas"]
    assert len(fv) == 2
    assert list(fv.columns) == [
        "id_ticket",
        "fecha",
        "id_sucursal",
        "id_producto",
        "cantidad",
        "precio_unitario",
    ]
    assert fv.iloc[0]["id_ticket"] == 1
    assert fv.iloc[0]["fecha"].year == 2024
    assert fv.iloc[1]["fecha"].month == 4


def test_transform_inconsistent_derivations_aborts():
    frames = _base_frames()
    frames[SHEET_TIEMPO] = frames[SHEET_TIEMPO].copy()
    frames[SHEET_TIEMPO].loc[0, "trimestre"] = 99
    with pytest.raises(ContractError, match="derivaciones inconsistentes"):
        transform(frames)