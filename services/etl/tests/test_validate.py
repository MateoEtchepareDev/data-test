import pandas as pd
import pytest

from etl.validate import (
    ContractError,
    SHEET_HECHOS,
    SHEET_PRODUCTO,
    SHEET_SUCURSAL,
    SHEET_TIEMPO,
    validate,
)


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
        ).astype({"cantidad": "int64", "id_fecha": "int64", "id_producto": "int64", "id_sucursal": "int64", "nro_venta": "int64"}),
        SHEET_PRODUCTO: pd.DataFrame(
            [
                {"id_producto": 1, "nombre": "Prod A", "categoria": "Cat1", "costo": 5.0},
                {"id_producto": 2, "nombre": "Prod B", "categoria": "Cat1", "costo": 2.0},
            ]
        ).astype({"id_producto": "int64"}),
        SHEET_SUCURSAL: pd.DataFrame(
            [
                {"id_sucursal": 1, "ciudad": "C1", "provincia": "Buenos Aires", "tipo": "T1"},
                {"id_sucursal": 2, "ciudad": "C2", "provincia": "Córdoba", "tipo": "T2"},
            ]
        ).astype({"id_sucursal": "int64"}),
        SHEET_TIEMPO: pd.DataFrame(
            [
                {"id_fecha": 1, "fecha": pd.Timestamp("2024-01-01"), "dia": 1, "mes": 1, "trimestre": 1, "anio": 2024},
                {"id_fecha": 2, "fecha": pd.Timestamp("2024-01-02"), "dia": 2, "mes": 1, "trimestre": 1, "anio": 2024},
            ]
        ).astype({"id_fecha": "int64"}),
    }


def _many_clean():
    """21 rows clean -> 1 bad row = ~4.7% under 5% threshold."""
    return {
        SHEET_HECHOS: pd.DataFrame(
            [
                {
                    "nro_venta": i,
                    "id_fecha": 1 + (i % 2),
                    "id_producto": 1 + (i % 2),
                    "id_sucursal": 1 + (i % 2),
                    "cantidad": 2,
                    "precio_unitario": 10.0,
                    "total": 20.0,
                }
                for i in range(1, 22)
            ]
        ).astype({"cantidad": "int64", "id_fecha": "int64", "id_producto": "int64", "id_sucursal": "int64", "nro_venta": "int64"}),
        SHEET_PRODUCTO: pd.DataFrame(
            [
                {"id_producto": 1, "nombre": "Prod A", "categoria": "Cat1", "costo": 5.0},
                {"id_producto": 2, "nombre": "Prod B", "categoria": "Cat1", "costo": 2.0},
            ]
        ).astype({"id_producto": "int64"}),
        SHEET_SUCURSAL: pd.DataFrame(
            [
                {"id_sucursal": 1, "ciudad": "C1", "provincia": "Buenos Aires", "tipo": "T1"},
                {"id_sucursal": 2, "ciudad": "C2", "provincia": "Córdoba", "tipo": "T2"},
            ]
        ).astype({"id_sucursal": "int64"}),
        SHEET_TIEMPO: pd.DataFrame(
            [
                {"id_fecha": 1, "fecha": pd.Timestamp("2024-01-01"), "dia": 1, "mes": 1, "trimestre": 1, "anio": 2024},
                {"id_fecha": 2, "fecha": pd.Timestamp("2024-01-02"), "dia": 2, "mes": 1, "trimestre": 1, "anio": 2024},
            ]
        ).astype({"id_fecha": "int64"}),
    }


def test_validate_ok():
    clean, report = validate(_base_frames())
    assert report.discarded == 0
    assert len(clean[SHEET_HECHOS]) == 2


def test_validate_missing_sheet():
    frames = _base_frames()
    del frames[SHEET_HECHOS]
    with pytest.raises(ContractError, match="hoja faltante: Hechos_Ventas"):
        validate(frames)


def test_validate_missing_column():
    frames = _base_frames()
    frames[SHEET_HECHOS] = frames[SHEET_HECHOS].drop(columns=["cantidad"])
    with pytest.raises(ContractError, match="columna.*faltante"):
        validate(frames)


def test_validate_non_coercible_type():
    frames = _base_frames()
    frames[SHEET_HECHOS] = frames[SHEET_HECHOS].copy()
    frames[SHEET_HECHOS]["cantidad"] = frames[SHEET_HECHOS]["cantidad"].astype(object)
    frames[SHEET_HECHOS].loc[0, "cantidad"] = "no_un_numero"
    with pytest.raises(ContractError, match="no coercible a entero"):
        validate(frames)


def test_validate_non_int_float():
    frames = _base_frames()
    frames[SHEET_HECHOS] = frames[SHEET_HECHOS].copy()
    frames[SHEET_HECHOS]["cantidad"] = frames[SHEET_HECHOS]["cantidad"].astype(object)
    frames[SHEET_HECHOS].loc[0, "cantidad"] = 3.5
    with pytest.raises(ContractError, match="valores no enteros"):
        validate(frames)


def test_validate_duplicate_nro_venta_discards():
    frames = _many_clean()
    extra = pd.DataFrame([{
        "nro_venta": 1, "id_fecha": 1, "id_producto": 1,
        "id_sucursal": 1, "cantidad": 1, "precio_unitario": 1.0, "total": 1.0
    }]).astype({"cantidad": "int64", "id_fecha": "int64", "id_producto": "int64", "id_sucursal": "int64", "nro_venta": "int64"})
    frames[SHEET_HECHOS] = pd.concat([frames[SHEET_HECHOS], extra], ignore_index=True)
    clean, report = validate(frames)
    assert report.discarded == 1
    assert len(clean[SHEET_HECHOS]) == 21


def test_validate_cantidad_non_positive_discards():
    frames = _many_clean()
    frames[SHEET_HECHOS] = frames[SHEET_HECHOS].copy()
    frames[SHEET_HECHOS].loc[0, "cantidad"] = 0
    clean, report = validate(frames)
    assert report.discarded == 1
    assert len(clean[SHEET_HECHOS]) == 20


def test_validate_fk_missing_discards():
    frames = _many_clean()
    frames[SHEET_HECHOS] = frames[SHEET_HECHOS].copy()
    frames[SHEET_HECHOS].loc[0, "id_fecha"] = 999
    clean, report = validate(frames)
    assert report.discarded == 1
    assert len(clean[SHEET_HECHOS]) == 20


def test_validate_unknown_provincia_aborts():
    frames = _base_frames()
    frames[SHEET_SUCURSAL] = frames[SHEET_SUCURSAL].copy()
    frames[SHEET_SUCURSAL].loc[0, "provincia"] = "NoExiste"
    with pytest.raises(ContractError, match="fuera del mapa"):
        validate(frames)


def test_validate_abort_threshold():
    frames = _base_frames()
    frames[SHEET_HECHOS] = pd.DataFrame(
        [
            {"nro_venta": 1, "id_fecha": 999, "id_producto": 1, "id_sucursal": 1, "cantidad": 1, "precio_unitario": 1.0, "total": 1.0},
            {"nro_venta": 2, "id_fecha": 999, "id_producto": 1, "id_sucursal": 1, "cantidad": 1, "precio_unitario": 1.0, "total": 1.0},
            {"nro_venta": 3, "id_fecha": 1, "id_producto": 1, "id_sucursal": 1, "cantidad": 1, "precio_unitario": 1.0, "total": 1.0},
        ]
    ).astype({"cantidad": "int64", "id_fecha": "int64", "id_producto": "int64", "id_sucursal": "int64", "nro_venta": "int64"})
    with pytest.raises(ContractError, match="aborto por umbral"):
        validate(frames)