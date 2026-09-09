import sys

from shared.migrate import migrate

from etl.extract import DEFAULT_XLSX, extract
from etl.load import load
from etl.transform import transform
from etl.validate import ContractError, validate


def main(excel_path=None):
    excel_path = excel_path or DEFAULT_XLSX

    migrate()
    print(f"extrayendo {excel_path}")
    raw = extract(excel_path)

    frames, report = validate(raw)
    print(f"validación: {report.total - report.discarded}/{report.total} filas válidas, "
          f"{report.discarded} descartadas")
    for err in report.errors:
        print(f"  descartada fila {err.row} [{err.sheet}] {err.column}={err.value!r} — {err.rule}")
    for warning in report.warnings:
        print(f"  advertencia: {warning}")

    data = transform(frames)
    counts = load(data)
    print("carga OK:")
    for table, n in counts.items():
        print(f"  {table}: {n} filas UPSERT")


if __name__ == "__main__":
    try:
        main()
    except ContractError as exc:
        print(f"error: {exc}")
        sys.exit(1)
    except RuntimeError as exc:
        print(f"error: {exc}")
        sys.exit(1)