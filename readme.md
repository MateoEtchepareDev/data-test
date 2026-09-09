# Dashboard de Ventas (CoffeeTime)

Pipeline de datos completo: Excel de origen → validación → modelo dimensional en Supabase → API REST (Flask) → dashboard web (vanilla JS + Chart.js + Leaflet).

## Estado actual — Hito #2 alcanzado

- [x] Fase 1: esquema estrella en Supabase (`dim_provincia`, `dim_producto`, `dim_tiempo`, `dim_sucursal`, `fact_ventas` + índice `fecha`); paquete `shared` (conexión pooled 6543, migraciones idempotentes).
- [x] Fase 2: ETL (`services/etl`) — extract → validate → transform → load con UPSERT idempotente. `2000/2000` filas válidas, re-ejecutable sin duplicar.

Pendiente: Fase 3 (API), Fase 4 (frontend), Fase 5 (deploy). Ver `docs/roadmap.md`.

## Requisitos

- Supabase activo (plan free) con connection string **pooled** (puerto 6543).
- Python ≥ 3.12. En este repo: `.venv` en la raíz.

## Setup y comandos

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -e "packages/shared[dev]" -e "services/etl[dev]"
```

Crear `.env` a partir de `.env.example` con la connection string pooled de Supabase.

```bash
.venv\Scripts\python -m shared.migrate      # aplica migraciones pendientes (idempotente)
.venv\Scripts\python -m etl.main            # migrate -> extract -> validate -> transform -> load
.venv\Scripts\python -m pytest packages/shared/tests services/etl/tests
```

## Documentación

- `docs/architecture.md` — decisiones de arquitectura y modelo dimensional.
- `docs/data-contract.md` — contrato del Excel de origen.
- `docs/roadmap.md` — orden de construcción y hitos.