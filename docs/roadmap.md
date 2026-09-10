# Roadmap — Dashboard de Ventas (CoffeeTime)

## Requisitos previos para empezar a construir

Bloqueantes de Fase 1 (no se avanza sin esto):

- **Supabase activo + connection string pooled** (Supavisor, puerto 6543). Sin proyecto levantado → no se puede correr migraciones ni desarrollarse nada.
- **Entorno Python local**: venv con dependencias de `shared` (`psycopg2-binary` para Python 3.14) y `pytest`. Python local actual: 3.14.5.
- **Tipos de dato por columna — definidos en Fase 1** contra el archivo real: `NUMERIC(12,2)` para montos, `INTEGER` para ids/cantidad/fechas derivadas, `VARCHAR` para cadenas (ver `architecture.md` §6).

No requerido hasta fases posteriores: cuenta AWS, GeoJSON (Fase 4), pandas/openpyxl (Fase 2). (Secrets Manager no se usa en ninguna fase: la connection string se maneja como variable de entorno de Lambda y GitHub Secret.)

## Fase 0 — Decisiones de base (no código)

- `pyproject.toml` por servicio: `etl` = pandas, openpyxl, psycopg2; `api` = flask, mangum, psycopg2; `shared` = psycopg2. `requires-python >=3.12`.
- Dev DB = Supabase real (directo, sin Docker). Correr migraciones contra ella desde el arranque. Sin Supabase disponible abajo → no se avanza.
- Conexión siempre pooled (Supavisor 6543), tanto en dev como en Lambda.
- GeoJSON público: repos originales (`andresgnlez/argentina-geojson`, `mgaitan/argentina-mapas`) **ya no existen** (404). Reemplazo usado en Fase 4: `alvarezgarcia/provincias-argentinas-geojson` (un archivo por provincia, ~192 KB en total), fusionado en `frontend/data/geo/provincias.json`. Validado: `properties.name` viene sin acentos (`Cordoba`) → normalizado en la fusión a `Córdoba` para matchear `dim_provincia` exactamente.
- Tests: pytest. Dev: `flask run` local; Lambda recién en Fase 5.

## Fase 1 — `packages/shared` + migraciones

- Migraciones `001`..`006` con DDL real (provincia, producto, tiempo, sucursal, fact_ventas, índice `fecha`), en el orden FK-safe documentado en `architecture.md` §5.
- `migrate.py` (runner que aplica pendientes en orden), `db.py` (conexión pooled, puerto 6543), `schema.py` (nombres de tablas/columnas).
- Tests: `test_db.py`.
- **Hito verificable #1** — esquema estrella levantado en Supabase. El readme empieza a llenarse acá.

## Fase 2 — ETL (`services/etl`) ✅

- [x] `extract.py`: lee `data/ventas.xlsx`, hojas `Hechos_Ventas`, `Dim_Producto`, `Dim_Sucursal`, `Dim_Tiempo`.
- [x] `validate.py`: contrato de `data-contract.md` — hojas/columnas faltantes, tipos, nulos, duplicados `nro_venta`, integridad referencial (`id_fecha`/`id_producto`/`id_sucursal`), `cantidad > 0`, umbral de aborto 5%.
- [x] `transform.py`: resolución `id_fecha → fecha` y validación de año/trimestre/mes derivados; normalización de provincias (mapa identidad de `data-contract.md` §4).
- [x] `load.py`: UPSERT idempotente en `fact_ventas` + carga de dimensiones.
- [x] `main.py`: orquestación migrate → extract → validate → transform → load.
- [x] Tests: `test_validate.py`, `test_transform.py` (datasets construidos en memoria; se descartó el fixture xlsx por YAGNI).
- **Hito verificable #2 (alcanzado)** — carga completa y re-ejecutable sin duplicar: `2000/2000` filas válidas, `fact_ventas` mantiene 2000 tickets distintos entre corridas.

## Fase 3 — API (`services/api`)

- `app.py`: Flask + Mangum + CORS + Cache-Control.
- `routes/kpis.py`: ventas totales, cantidad vendida, ticket promedio, margen bruto — con filtro por período donde aplique.
- `routes/analytics.py`: top 5 productos Q4-2024, provincia con mayor volumen, categoría más rentable, margen por categoría, evolución mensual.
- `queries/kpis_sql.py` + `analytics_sql.py`: SQL directo, sin ORM. Cada query mapea a una fila de la tabla §4 del modelo dimensional.
- Tests: `test_routes.py`.
- **Hito verificable #3** — API completa servida como JSON (`curl`).

## Fase 4 — Frontend ✅

- [x] `index.html` + `css/styles.css`: layout del dashboard (tarjetas KPI + grilla de paneles; Chart.js/Leaflet vía CDN).
- [x] `js/api.js`: capa fetch con `cache: 'reload'`, consume **solo** la API (`API_BASE` sobreescribible vía `window.API_BASE`).
- [x] `js/kpis.js`: tarjetas de KPIs (ventas, cantidad, margen, ticket promedio por sucursal) + tabla top 5 productos.
- [x] `js/chart-lineas.js`: evolución mensual (Chart.js).
- [x] `js/chart-barras.js`: rentabilidad por categoría (Chart.js, `/analytics/margen-por-categoria`).
- [x] `js/mapa.js` + `data/geo/provincias.json`: mapa por provincia (Leaflet), destaca la provincia con mayor volumen.
- [x] Botón "Actualizar datos": recarga todos los endpoints sin cambios de código.
- **Hito verificable #4 (alcanzado)** — dashboard funcional contra API local, sin acceso directo a la base (verificado con Playwright: valores exactos, charts, mapa, sin errores de consola, refresh re-consumiendo la API).

## Fase 5 — Infra y deploy

- `infra/template.yaml`: SAM — Lambda con **function URL** (auth `NONE`, CORS `*`) + rol IAM de logging + LogGroup CloudWatch con retención 1 día + variable de entorno `SUPABASE_DB_URL` por parámetro de deploy (sin Secrets Manager).
- `infra/build.sh`: copia `services/api/src/api` y `packages/shared/src/shared` al build dir antes de `sam build`.
- Workflows:
  - `.github/workflows/etl.yml`: `workflow_dispatch`, corre migrate + load con secrets de Supabase.
  - `.github/workflows/deploy-api.yml`: build.sh + sam deploy (URL de la función como output; `SupabaseDbUrl` desde GitHub Secret).
  - `.github/workflows/deploy-frontend.yml`: GitHub Pages publicando `frontend/`; inyecta `window.API_BASE` (variable de repo `API_BASE_URL`) en `js/config.js`.
- Documentar estrategia de logging/observabilidad y de tests.
- **Hito verificable #5** — pipeline end-to-end en producción.

## Fase 6 — Polish

- Umbral de aborto 5% validado contra el dataset real.
- Alerta de facturación (AWS Budgets).
- Verificación de idempotencia real en Supabase.