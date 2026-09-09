# Dashboard de Ventas (CoffeeTime)

Pipeline de datos completo: Excel de origen → validación → modelo dimensional en Supabase → API REST (Flask) → dashboard web (vanilla JS + Chart.js + Leaflet).

## Estado actual — Hito #4 alcanzado

- [x] Fase 1: esquema estrella en Supabase (`dim_provincia`, `dim_producto`, `dim_tiempo`, `dim_sucursal`, `fact_ventas` + índice `fecha`); paquete `shared` (conexión pooled 6543, migraciones idempotentes).
- [x] Fase 2: ETL (`services/etl`) — extract → validate → transform → load con UPSERT idempotente. `2000/2000` filas válidas, re-ejecutable sin duplicar.
- [x] Fase 3: API (`services/api`) — Flask + Mangum, SQL directo sin ORM. KPIs (`/kpis/*`) con filtro opcional por `anio`/`trimestre`/`mes` y analytics (`/analytics/*`, incluido `margen-por-categoria`). JSON con CORS y `Cache-Control: no-store`.
- [x] Fase 4: Frontend (`frontend/`) — dashboard vanilla JS + Chart.js + Leaflet (CDN). Consume **solo** la API; botón "Actualizar datos" para recargar sin cambios de código. Verificado con Playwright contra la API local.

Pendiente: Fase 5 (deploy AWS + GitHub Actions), Fase 6 (polish). Ver `docs/roadmap.md`.

## Requisitos

- Supabase activo (plan free) con connection string **pooled** (puerto 6543).
- Python ≥ 3.12. En este repo: `.venv` en la raíz.

## Setup y comandos

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -e "packages/shared[dev]" -e "services/etl[dev]" -e "services/api[dev]"
```

Crear `.env` a partir de `.env.example` con la connection string pooled de Supabase.

```bash
.venv\Scripts\python -m shared.migrate      # aplica migraciones pendientes (idempotente)
.venv\Scripts\python -m etl.main            # migrate -> extract -> validate -> transform -> load
.venv\Scripts\python -m pytest packages/shared/tests services/etl/tests services/api/tests
```

Servir la API local y probar (requiere `.env` con `SUPABASE_DB_URL`):

```bash
.venv\Scripts\python -m api.app             # Flask dev server en http://127.0.0.1:5000
curl "http://127.0.0.1:5000/kpis/ventas-totales?anio=2024&trimestre=4"
curl "http://127.0.0.1:5000/analytics/top-productos"        # Q4-2024 por default
curl "http://127.0.0.1:5000/analytics/evolucion-mensual"
```

Servir el frontend (la API debe seguir corriendo en `:5000`) y abrir `http://127.0.0.1:8080/`:

```bash
.venv\Scripts\python -m http.server 8080 --directory frontend
```

## Documentación

- `docs/architecture.md` — decisiones de arquitectura y modelo dimensional.
- `docs/data-contract.md` — contrato del Excel de origen.
- `docs/roadmap.md` — orden de construcción y hitos.