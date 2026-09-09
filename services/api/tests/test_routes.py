from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from api import app as app_module
from api.queries import analytics_sql, kpis_sql


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("api.routes.kpis.connect", MagicMock)
    monkeypatch.setattr("api.routes.analytics.connect", MagicMock)
    application = app_module.create_app()
    application.config["TESTING"] = True
    return application.test_client()


def test_ventas_totales(client, monkeypatch):
    monkeypatch.setattr(kpis_sql, "ventas_totales", lambda conn, filtro=None: Decimal("1234.567"))
    resp = client.get("/kpis/ventas-totales")
    assert resp.status_code == 200
    assert resp.get_json() == {"ventas_totales": 1234.57}


def test_cantidad_vendida(client, monkeypatch):
    monkeypatch.setattr(kpis_sql, "cantidad_vendida", lambda conn, filtro=None: 5000)
    resp = client.get("/kpis/cantidad-vendida")
    assert resp.get_json() == {"cantidad_vendida": 5000.0}


def test_margen_bruto(client, monkeypatch):
    monkeypatch.setattr(kpis_sql, "margen_bruto", lambda conn, filtro=None: Decimal("99.999"))
    resp = client.get("/kpis/margen-bruto")
    assert resp.get_json() == {"margen_bruto": 100.0}


def test_ticket_promedio_por_sucursal(client, monkeypatch):
    rows = [
        {"id_sucursal": 1, "nombre_sucursal": "C1", "ticket_promedio": Decimal("10.5")},
        {"id_sucursal": 2, "nombre_sucursal": "C2", "ticket_promedio": Decimal("20.25")},
    ]
    monkeypatch.setattr(kpis_sql, "ticket_promedio", lambda conn, filtro=None: rows)
    resp = client.get("/kpis/ticket-promedio")
    assert resp.status_code == 200
    assert resp.get_json() == [
        {"id_sucursal": 1, "nombre_sucursal": "C1", "ticket_promedio": 10.5},
        {"id_sucursal": 2, "nombre_sucursal": "C2", "ticket_promedio": 20.25},
    ]


def test_filtro_periodo_se_forwardea_a_la_query(client, monkeypatch):
    visto = {}

    def fake(conn, filtro=None):
        visto["filtro"] = filtro
        return 1

    monkeypatch.setattr(kpis_sql, "cantidad_vendida", fake)
    resp = client.get("/kpis/cantidad-vendida?anio=2024&trimestre=4&mes=10")
    assert resp.status_code == 200
    assert visto["filtro"] == {"anio": 2024, "trimestre": 4, "mes": 10}


def test_periodo_sin_filtro_envia_dict_vacio(client, monkeypatch):
    visto = {}
    monkeypatch.setattr(
        kpis_sql,
        "ventas_totales",
        lambda conn, filtro=None: visto.setdefault("filtro", filtro),
    )
    client.get("/kpis/ventas-totales")
    assert visto["filtro"] == {}


@pytest.mark.parametrize(
    "url",
    [
        "/kpis/ventas-totales?anio=abc",
        "/kpis/ventas-totales?trimestre=99",
        "/kpis/ventas-totales?mes=0",
    ],
)
def test_param_periodo_invalido_devuelve_400(client, url):
    resp = client.get(url)
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_error_interno_devuelve_500_json(client, monkeypatch):
    def boom(conn, filtro=None):
        raise RuntimeError("db caida")

    monkeypatch.setattr(kpis_sql, "ventas_totales", boom)
    resp = client.get("/kpis/ventas-totales")
    assert resp.status_code == 500
    assert resp.get_json() == {"error": "error interno"}


def test_top_productos_default_q4_2024(client, monkeypatch):
    visto = {}

    def fake(conn, anio, trimestre, limit):
        visto.update(anio=anio, trimestre=trimestre, limit=limit)
        return [
            {"id_producto": 1, "nombre_producto": "A", "ventas": Decimal("11.11")},
            {"id_producto": 2, "nombre_producto": "B", "ventas": Decimal("2.0")},
        ]

    monkeypatch.setattr(analytics_sql, "top_productos", fake)
    resp = client.get("/analytics/top-productos")
    assert resp.status_code == 200
    assert visto == {"anio": 2024, "trimestre": 4, "limit": 5}
    assert resp.get_json() == [
        {"id_producto": 1, "nombre_producto": "A", "ventas": 11.11},
        {"id_producto": 2, "nombre_producto": "B", "ventas": 2.0},
    ]


def test_top_productos_con_params(client, monkeypatch):
    visto = {}
    monkeypatch.setattr(
        analytics_sql,
        "top_productos",
        lambda conn, anio, trimestre, limit: visto.update(
            anio=anio, trimestre=trimestre, limit=limit
        )
        or [],
    )
    resp = client.get("/analytics/top-productos?anio=2025&trimestre=1")
    assert resp.status_code == 200
    assert visto == {"anio": 2025, "trimestre": 1, "limit": 5}


def test_provincia_mayor_volumen(client, monkeypatch):
    monkeypatch.setattr(
        analytics_sql,
        "provincia_mayor_volumen",
        lambda conn: {"provincia": "Córdoba", "ventas": Decimal("5000.5")},
    )
    resp = client.get("/analytics/provincia-mayor-volumen")
    assert resp.get_json() == {"provincia": "Córdoba", "ventas": 5000.5}


def test_provincia_mayor_volumen_sin_datos(client, monkeypatch):
    monkeypatch.setattr(analytics_sql, "provincia_mayor_volumen", lambda conn: None)
    resp = client.get("/analytics/provincia-mayor-volumen")
    assert resp.get_json() == {"provincia": None, "ventas": None}


def test_categoria_mas_rentable(client, monkeypatch):
    monkeypatch.setattr(
        analytics_sql,
        "categoria_mas_rentable",
        lambda conn: {"categoria": "Bebidas", "margen": Decimal("123.456")},
    )
    resp = client.get("/analytics/categoria-mas-rentable")
    assert resp.get_json() == {"categoria": "Bebidas", "margen": 123.46}


def test_margen_por_categoria(client, monkeypatch):
    rows = [
        {"categoria": "Bebida", "margen": Decimal("4732.27")},
        {"categoria": "Comida", "margen": Decimal("4299.27")},
    ]
    monkeypatch.setattr(analytics_sql, "margen_por_categoria", lambda conn: rows)
    resp = client.get("/analytics/margen-por-categoria")
    assert resp.status_code == 200
    assert resp.get_json() == [
        {"categoria": "Bebida", "margen": 4732.27},
        {"categoria": "Comida", "margen": 4299.27},
    ]


def test_evolucion_mensual(client, monkeypatch):
    rows = [
        {"anio": 2024, "mes": 1, "ventas": Decimal("100.0")},
        {"anio": 2024, "mes": 2, "ventas": Decimal("200.0")},
    ]
    monkeypatch.setattr(analytics_sql, "evolucion_mensual", lambda conn: rows)
    resp = client.get("/analytics/evolucion-mensual")
    assert resp.get_json() == [
        {"anio": 2024, "mes": 1, "ventas": 100.0},
        {"anio": 2024, "mes": 2, "ventas": 200.0},
    ]


def test_headers_cors_y_cache(client, monkeypatch):
    monkeypatch.setattr(kpis_sql, "ventas_totales", lambda conn, filtro=None: 1)
    resp = client.get("/kpis/ventas-totales")
    assert resp.status_code == 200
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert resp.headers["Cache-Control"] == "no-store"