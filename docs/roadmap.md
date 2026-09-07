# Roadmap — Dashboard de Ventas (CoffeeTime)

## Requisitos previos para empezar a construir

Bloqueantes de Fase 1 (no se avanza sin esto):

- **Supabase activo + connection string pooled** (Supavisor, puerto 6543). Sin proyecto levantado → no se puede correr migraciones ni desarrollarse nada.
- **Entorno Python local**: venv con dependencias de `shared` (`psycopg2-binary` para Python 3.14) y `pytest`. Python local actual: 3.14.5.
- **Tipos de dato por columna — definidos en Fase 1** contra el archivo real: `NUMERIC(12,2)` para montos, `INTEGER` para ids/cantidad/fechas derivadas, `VARCHAR` para cadenas (ver `architecture.md` §6).

No requerido hasta fases posteriores: cuenta AWS, Secrets Manager, GeoJSON (Fase 4), pandas/openpyxl (Fase 2).

## Fase 0 — Decisiones de base (no código)

- `pyproject.toml` por servicio: `etl` = pandas, openpyxl, psycopg2; `api` = flask, mangum, psycopg2; `shared` = psycopg2. `requires-python >=3.12`.
- Dev DB = Supabase real (directo, sin Docker). Correr migraciones contra ella desde el arranque. Sin Supabase disponible abajo → no se avanza.
- Conexión siempre pooled (Supavisor 6543), tanto en dev como en Lambda.
- GeoJSON público: `andresgnlez/argentina-geojson` (`argentina/provincias.json`) — **verificar** que `properties.name` sea `"Córdoba"` acentuado; si no, probar `mgaitan/argentina-mapas`. El nombre normalizado de `Cordoba→Córdoba` depende del match real (validar en Fase 4).
- Tests: pytest. Dev: `flask run` local; Lambda recién en Fase 5.

## Fase 1 — `packages/shared` + migraciones

- Migraciones `001`..`006` con DDL real (provincia, producto, tiempo, sucursal, fact_ventas, índice `fecha`), en el orden FK-safe documentado en `architecture.md` §5.
- `migrate.py` (runner que aplica pendientes en orden), `db.py` (conexión pooled, puerto 6543), `schema.py` (nombres de tablas/columnas).
- Tests: `test_db.py`.
- **Hito verificable #1** — esquema estrella levantado en Supabase. El readme empieza a llenarse acá.

## Fase 2 — ETL (`services/etl`)

- `extract.py`: lee `data/ventas.xlsx`, hojas `Hechos_Ventas`, `Dim_Producto`, `Dim_Sucursal`, `Dim_Tiempo`.
- `validate.py`: contrato de `data-contract.md` — hojas/columnas faltantes, tipos, nulos, duplicados `nro_venta`, integridad referencial (`id_fecha`/`id_producto`/`id_sucursal`), `cantidad > 0`, umbral de aborto 5%.
- `transform.py`: resolución `id_fecha → fecha` y validación de año/trimestre/mes derivados; normalización de provincias (mapa identidad de `data-contract.md` §4).
- `load.py`: UPSERT idempotente en `fact_ventas` + carga de dimensiones.
- `main.py`: orquestación migrate → extract → validate → transform → load.
- Tests: `test_validate.py`, `test_transform.py`, fixtures.
- **Hito verificable #2** — carga completa y re-ejecutable sin duplicar.

## Fase 3 — API (`services/api`)

- `app.py`: Flask + Mangum + CORS + Cache-Control.
- `routes/kpis.py`: ventas totales, cantidad vendida, ticket promedio, margen bruto — con filtro por período donde aplique.
- `routes/analytics.py`: top 5 productos Q4-2024, provincia con mayor volumen, categoría más rentable, evolución mensual.
- `queries/kpis_sql.py` + `analytics_sql.py`: SQL directo, sin ORM. Cada query mapea a una fila de la tabla §4 del modelo dimensional.
- Tests: `test_routes.py`.
- **Hito verificable #3** — API completa servida como JSON (`curl`).

## Fase 4 — Frontend

- `index.html` + `css/styles.css`: layout del dashboard.
- `js/api.js`: capa fetch con `cache: 'reload'`, consume **solo** la API.
- `js/kpis.js`: tarjetas de KPIs.
- `js/chart-lineas.js`: evolución mensual (Chart.js).
- `js/chart-barras.js`: rentabilidad por categoría (Chart.js).
- `js/mapa.js` + `data/geo/provincias.json`: mapa coroplético por provincia (Leaflet).
- **Hito verificable #4** — dashboard funcional contra API local, sin acceso directo a la base.

## Fase 5 — Infra y deploy

- `infra/template.yaml`: SAM — Lambda + API Gateway + IAM + referencia a Secrets Manager.
- `infra/build.sh`: copia `packages/shared/src/shared` al build dir antes de `sam build`.
- Workflows:
  - `.github/workflows/etl.yml`: `workflow_dispatch`, corre migrate + load con secrets de Supabase.
  - `.github/workflows/deploy-api.yml`: build.sh + sam deploy.
  - `.github/workflows/deploy-frontend.yml`: sync a S3 + invalidación CloudFront.
- Documentar estrategia de logging/observabilidad y de tests.
- **Hito verificable #5** — pipeline end-to-end en producción.

## Fase 6 — Polish

- Umbral de aborto 5% validado contra el dataset real.
- Alerta de facturación (AWS Budgets).
- Verificación de idempotencia real en Supabase.