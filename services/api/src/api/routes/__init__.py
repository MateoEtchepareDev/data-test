from functools import wraps
import logging

from flask import request

logger = logging.getLogger(__name__)


def _num(value):
    if value is None:
        return None
    return round(float(value), 2)


def _periodo_filtro():
    filtro = {}
    rangos = {"trimestre": (1, 4), "mes": (1, 12)}
    for name in ("anio", "trimestre", "mes"):
        raw = request.args.get(name)
        if raw is None:
            continue
        try:
            value = int(raw)
        except ValueError:
            raise ValueError(f"Parámetro '{name}' debe ser un entero")
        if name == "anio" and value <= 0:
            raise ValueError("Parámetro 'anio' debe ser un año positivo")
        if name in rangos and not rangos[name][0] <= value <= rangos[name][1]:
            raise ValueError(
                f"Parámetro '{name}' debe estar entre {rangos[name][0]} y {rangos[name][1]}"
            )
        filtro[name] = value
    return filtro


def api_error_handler(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            return {"error": str(exc)}, 400
        except Exception:
            logger.exception("error interno en %s %s", request.method, request.path)
            return {"error": "error interno"}, 500

    return wrapper