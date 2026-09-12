# Dashboard de Ventas (CoffeeTime)

Sistema de análisis de ventas que convierte un archivo Excel en un dashboard web interactivo. El proyecto cubre el ciclo completo de un flujo de datos: **ingesta → validación → modelado → persistencia → API → visualización**.

## Qué hace

Un archivo Excel (`data/ventas.xlsx`) se valida, se normaliza y se carga en una base de datos relacional con modelo dimensional (esquema estrella) en Supabase. Una API REST expone KPIs y consultas analíticas, y un dashboard web las muestra en tarjetas y gráficos:

- **KPIs**: ventas totales, cantidad vendida, margen bruto y ticket promedio por sucursal.
- **Análisis**: top 5 productos del último trimestre de 2024, evolución mensual de ventas, rentabilidad por categoría y un **mapa por provincia** en el que se puede hacer clic para ver las ventas de cada provincia.
- **Actualización**: el dashboard consume los datos **solo** desde la API y se puede recargar sin cambiar código.

## Cómo está compuesto

```
Excel (data/ventas.xlsx)
        │
        ▼
  ETL (services/etl)       → valida y carga en Supabase (PostgreSQL)
        │
        ▼
  API REST (services/api)  → Flask + Mangum, SQL directo, expone /kpis/* y /analytics/*
        │
        ▼
  Frontend (frontend/)     → HTML/CSS/JS vanilla + Chart.js + Leaflet
```

- **Base de datos**: PostgreSQL en Supabase, esquema estrella (`dim_*` + `fact_ventas`), conexión pooled.
- **Backend/API**: Flask servido como función serverless (Lambda vía Mangum).
- **Frontend**: dashboard estático sin framework, con Chart.js y Leaflet.
- **Infra**: SAM (AWS Lambda), GitHub Actions para ETL y deploys, GitHub Pages para el frontend.

## Requisitos

- Supabase activo con connection string **pooled** (puerto 6543).
- Python ≥ 3.12.

## Empezar rápido

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -e "packages/shared[dev]" -e "services/etl[dev]" -e "services/api[dev]"
```

Crear `.env` a partir de `.env.example` y cargar los datos:

```bash
.venv\Scripts\python -m shared.migrate   # aplica las migraciones del esquema
.venv\Scripts\python -m etl.main         # extract -> validate -> transform -> load
```

Servir la API y el frontend (puertos 5000 y 8080) y abrir `http://127.0.0.1:8080/`.

## Stack

Python (pandas, openpyxl, psycopg2) · Flask · Supabase · JavaScript vanilla · Chart.js · Leaflet · AWS Lambda (SAM) · GitHub Actions · GitHub Pages.

## Documentación

- `docs/architecture.md` — decisiones de arquitectura y modelo dimensional.
- `docs/data-contract.md` — contrato del Excel de origen.
- `docs/roadmap.md` — estado del proyecto y orden de construcción.