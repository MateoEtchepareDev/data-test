from dataclasses import dataclass

import numpy as np
import pandas as pd

ABORT_THRESHOLD = 0.05

SHEET_HECHOS = "Hechos_Ventas"
SHEET_PRODUCTO = "Dim_Producto"
SHEET_SUCURSAL = "Dim_Sucursal"
SHEET_TIEMPO = "Dim_Tiempo"

REQUIRED_SHEETS = [SHEET_HECHOS, SHEET_PRODUCTO, SHEET_SUCURSAL, SHEET_TIEMPO]

PROVINCIA_MAP = {
    "Buenos Aires": "Buenos Aires",
    "Córdoba": "Córdoba",
    "Mendoza": "Mendoza",
    "Santa Fe": "Santa Fe",
}

SPEC = {
    SHEET_HECHOS: {
        "nro_venta": "int",
        "id_fecha": "int",
        "id_producto": "int",
        "id_sucursal": "int",
        "cantidad": "int",
        "precio_unitario": "numeric",
        "total": "numeric",
    },
    SHEET_PRODUCTO: {
        "id_producto": "int",
        "nombre": "str",
        "categoria": "str",
        "costo": "numeric",
    },
    SHEET_SUCURSAL: {"id_sucursal": "int", "ciudad": "str", "provincia": "str", "tipo": "str"},
    SHEET_TIEMPO: {
        "id_fecha": "int",
        "fecha": "date",
        "dia": "int",
        "mes": "int",
        "trimestre": "int",
        "anio": "int",
    },
}

FK_RULES = [
    ("id_fecha", SHEET_TIEMPO, "id_fecha"),
    ("id_producto", SHEET_PRODUCTO, "id_producto"),
    ("id_sucursal", SHEET_SUCURSAL, "id_sucursal"),
]


class ContractError(Exception):
    """Error bloqueante: aborta la corrida sin cargar nada."""


@dataclass
class RowError:
    sheet: str
    row: int
    column: str
    value: object
    rule: str


@dataclass
class Report:
    total: int
    discarded: int
    errors: list
    warnings: list

    def discard_ratio(self):
        return self.discarded / self.total if self.total else 0.0


def _kind(df, col):
    s = df[col]
    if pd.api.types.is_integer_dtype(s):
        return "int"
    if pd.api.types.is_float_dtype(s):
        return "float"
    if pd.api.types.is_bool_dtype(s):
        return "bool"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    return "object"


def _check_types(df, spec, sheet):
    for col, kind in spec.items():
        actual = _kind(df, col)
        if kind == "numeric":
            if actual not in ("int", "float"):
                raise ContractError(f"{sheet}.{col}: tipo no coercible a numérico ({actual})")
            continue
        if kind == "int":
            if actual in ("int", "float"):
                if actual == "float":
                    rest = df[col].dropna()
                    if not rest.empty and (rest % 1 != 0).any():
                        raise ContractError(f"{sheet}.{col}: valores numéricos no enteros")
                continue
            if actual == "object":
                try:
                    df[col] = pd.to_numeric(df[col], errors="raise")
                except (ValueError, TypeError) as exc:
                    raise ContractError(f"{sheet}.{col}: tipo no coercible a entero") from exc
                if (df[col] % 1 != 0).any():
                    raise ContractError(f"{sheet}.{col}: valores no enteros")
                continue
            raise ContractError(f"{sheet}.{col}: tipo no coercible a entero ({actual})")
        if kind == "str":
            if actual == "object":
                continue
            raise ContractError(f"{sheet}.{col}: tipo no coercible a texto ({actual})")
        if kind == "date":
            if actual == "date":
                continue
            raise ContractError(f"{sheet}.{col}: tipo no coercible a fecha ({actual})")


def _row_errors(sheet, df, mask, column, rule):
    return [
        RowError(sheet=sheet, row=int(idx) + 2, column=column, value=df.loc[idx, column], rule=rule)
        for idx in df.index[mask]
    ]


def validate(frames):
    for sheet, spec in SPEC.items():
        if sheet not in frames:
            raise ContractError(f"hoja faltante: {sheet}")
        missing_cols = [c for c in spec if c not in frames[sheet].columns]
        if missing_cols:
            raise ContractError(f"{sheet}: columna(s) obligatoria(s) faltante(s): {', '.join(missing_cols)}")

    errors = []
    warnings = []
    clean = {}

    for sheet, spec in SPEC.items():
        df = frames[sheet]
        bad = pd.Series(False, index=df.index)
        for col in spec:
            null_mask = df[col].isna()
            bad = bad | null_mask
            errors.extend(_row_errors(sheet, df, null_mask, col, "valor nulo en columna obligatoria"))
        valid = df[~bad].copy()
        if valid.empty:
            raise ContractError(f"{sheet}: sin filas válidas para procesar")
        _check_types(valid, spec, sheet)
        clean[sheet] = valid

    for sheet, pk in [(SHEET_PRODUCTO, "id_producto"), (SHEET_SUCURSAL, "id_sucursal")]:
        dups = clean[sheet][pk].duplicated(keep=False)
        if dups.any():
            raise ContractError(f"{sheet}: clave primaria duplicada en {pk}")

    t = clean[SHEET_TIEMPO]
    if t["fecha"].duplicated().any() or t["id_fecha"].duplicated().any():
        raise ContractError(f"{SHEET_TIEMPO}: id_fecha o fecha duplicada")
    for col, lo, hi in [("dia", 1, 31), ("mes", 1, 12), ("trimestre", 1, 4), ("anio", 1, 9999)]:
        bad_range = ~t[col].between(lo, hi)
        if bad_range.any():
            raise ContractError(f"{SHEET_TIEMPO}.{col}: valor fuera de rango {lo}-{hi}")

    provincias = clean[SHEET_SUCURSAL]["provincia"].unique()
    unknown = [p for p in provincias if p not in PROVINCIA_MAP]
    if unknown:
        raise ContractError(
            f"{SHEET_SUCURSAL}.provincia: valor(es) fuera del mapa de normalización: {unknown}"
        )

    h = clean[SHEET_HECHOS]
    total = len(h)
    bad = pd.Series(False, index=h.index)

    dup_nro = h["nro_venta"].duplicated(keep="first")
    bad = bad | dup_nro
    errors.extend(_row_errors(SHEET_HECHOS, h, dup_nro, "nro_venta", "nro_venta duplicado"))

    cant_bad = h["cantidad"] <= 0
    bad = bad | cant_bad
    errors.extend(_row_errors(SHEET_HECHOS, h, cant_bad, "cantidad", "cantidad debe ser > 0"))

    for col, fk_sheet, fk_col in FK_RULES:
        keys = set(clean[fk_sheet][fk_col])
        missing = ~h[col].isin(keys)
        bad = bad | missing
        errors.extend(_row_errors(SHEET_HECHOS, h, missing, col, f"referencia inexistente a {fk_sheet}.{fk_col}"))

    discarded = int(bad.sum())
    report = Report(total=total, discarded=discarded, errors=errors, warnings=warnings)
    if report.discard_ratio() > ABORT_THRESHOLD:
        raise ContractError(
            f"aborto por umbral: {discarded}/{total} filas descartadas "
            f"({report.discard_ratio():.1%}) > {ABORT_THRESHOLD:.0%}"
        )

    costo = clean[SHEET_PRODUCTO].set_index("id_producto")["costo"]
    for id_prod, group in h[h["precio_unitario"] > 0].groupby("id_producto"):
        if id_prod in costo.index and costo[id_prod] > group["precio_unitario"].max():
            warnings.append(f"{SHEET_PRODUCTO}: costo > precio_unitario del producto {id_prod}")

    mis_total = ~np_isclose(h["total"], h["cantidad"] * h["precio_unitario"])
    for idx in h.index[mis_total]:
        warnings.append(
            f"Hechos_Ventas fila {int(idx) + 2}: total ({h.loc[idx, 'total']}) "
            f"!= cantidad * precio_unitario ({h.loc[idx, 'cantidad']} * {h.loc[idx, 'precio_unitario']})"
        )

    clean[SHEET_HECHOS] = h[~bad]
    return clean, report


def np_isclose(a, b):
    return np.isclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), atol=0.005)