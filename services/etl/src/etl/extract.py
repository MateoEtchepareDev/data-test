from pathlib import Path

import pandas as pd

from etl.validate import ContractError, REQUIRED_SHEETS

DEFAULT_XLSX = Path(__file__).resolve().parents[4] / "data" / "ventas.xlsx"


def extract(path):
    try:
        raw = pd.read_excel(path, sheet_name=None)
    except Exception as exc:
        raise ContractError(f"no se pudo leer el Excel {path}: {exc}") from exc
    missing = [s for s in REQUIRED_SHEETS if s not in raw]
    if missing:
        raise ContractError(f"hoja(s) faltante(s): {', '.join(missing)}")
    return {s: raw[s] for s in REQUIRED_SHEETS}