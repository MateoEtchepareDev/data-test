# Dashboard de Ventas (CoffeeTime)

Pipeline de datos completo: Excel de origen → validación → modelo dimensional en Supabase → API REST (Flask) → dashboard web (vanilla JS + Chart.js + Leaflet).

## Estado actual — Fase 1 (Hito #1 alcanzado)

- [x] Esquema estrella levantado en Supabase: `dim_provincia`, `dim_producto`, `dim_tiempo`, `dim_sucursal`, `fact_ventas` + índice sobre `fact_ventas.fecha`.
- [x] Paquete `shared` (`packages/shared`): conexión pooled (Supavisor 6543), runner de migraciones idempotente, tests de esquema.

Pendiente: Fase 2 (ETL), Fase 3 (API), Fase 4 (frontend), Fase 5 (deploy). Ver `docs/roadmap.md`.

## Requisitos

- Supabase activo (plan free) con connection string **pooled** (puerto 6543).
- Python ≥ 3.12. En este repo: `.venv` en la raíz.

## Setup y comandos

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -e "packages/shared[dev]"
```

Crear `.env` a partir de `.env.example` con la connection string pooled de Supabase.

```bash
.venv\Scripts\python -m shared.migrate      # aplica migraciones pendientes (idempotente)
.venv\Scripts\python -m pytest packages/shared/tests
```

## Documentación

- `docs/architecture.md` — decisiones de arquitectura y modelo dimensional.
- `docs/data-contract.md` — contrato del Excel de origen.
- `docs/roadmap.md` — orden de construcción y hitos.