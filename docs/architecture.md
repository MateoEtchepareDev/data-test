# Architecture — Dashboard de Ventas (v2 — Serverless + Supabase)

## 1. Descripción

Sistema de análisis de ventas que parte de un archivo Excel de origen, pasa por un pipeline de ingesta/validación/carga hacia una base de datos relacional con modelo dimensional (esquema estrella), expone los resultados mediante una API REST, y los presenta en un dashboard web interactivo.

El proyecto cubre el ciclo completo de un flujo de datos: **ingesta → validación → modelado → persistencia → API → visualización**, con foco en demostrar criterio de arquitectura tanto en la capa de datos como en el backend.

---

## 2. Requisitos

### 2.1 Funcionales

- Leer, validar (tipos, nulos, duplicados) y cargar las tablas del Excel de origen al modelo dimensional.
- La carga debe ser re-ejecutable sin duplicar ni corromper datos (idempotencia).
- Calcular KPIs: Ventas Totales, Cantidad Vendida, Ticket Promedio por sucursal, Margen Bruto.
- Resolver consultas analíticas: top 5 productos del último trimestre de 2024, provincia con mayor volumen de ventas, categoría más rentable, evolución mensual de ventas.
- Exponer KPIs y consultas como endpoints REST en JSON, con filtro por período donde aplique, sin lógica de negocio adicional en esa capa.
- Dashboard con tarjetas de KPIs, gráfico de líneas (evolución mensual), mapa geográfico por provincia, gráfico de barras (rentabilidad por categoría).
- El dashboard consume datos **exclusivamente** desde la API, sin acceso directo a la base de datos.
- El dashboard debe poder actualizarse (recargar datos) sin requerir cambios de código.

### 2.2 De datos

- Debe existir un identificador de transacción/ticket para calcular el Ticket Promedio sin confundir filas. En el origen real cada ticket trae una única línea de producto, por lo que el grano de `fact_ventas` es por ticket (`nro_venta` único).
- Cada producto debe tener costo asociado y cada venta su precio de venta real, para calcular el Margen Bruto. El origen no trae precio de catálogo; el margen usa `precio_unitario` del hecho contra `costo` del producto.
- Cada sucursal debe tener una provincia asociada, para el análisis geográfico.
- Las fechas deben normalizarse a un formato único que permita derivar año/trimestre/mes.

### 2.3 Fuera de alcance (por ahora)

- Autenticación/autorización de usuarios en el dashboard.
- Actualización de datos en tiempo real (se asume carga batch/periódica, disparada manualmente).
- Soporte multi-idioma o multi-moneda.
- Escalabilidad a grandes volúmenes de datos (fuera del tamaño típico de un Excel de origen).
- Soporte genérico para múltiples fuentes de Excel con esquemas arbitrarios (el pipeline valida contra un contrato de datos conocido, no contra "cualquier" archivo).

---

## 3. Stack tecnológico y justificación

| Capa | Herramienta | Por qué |
|---|---|---|
| Ingesta/ETL | Python (pandas, openpyxl) | Estándar de facto para manipulación tabular y lectura de Excel; permite escribir validaciones explícitas sin depender de un framework pesado para un dataset de tamaño acotado. |
| Validación | Funciones propias en pandas | El volumen y la complejidad del dataset no justifican un framework de validación externo (ej. Great Expectations); una validación explícita y propia es más legible y más fácil de defender en una entrevista que una dependencia genérica mal aprovechada. |
| Base de datos | **PostgreSQL (Supabase)** | Motor relacional idéntico a RDS/Aurora en términos de SQL, funciones de ventana y modelado dimensional, pero gestionado fuera de AWS. Elegido sobre RDS/Aurora por costo: plan free de Supabase ($0) vs. Aurora Serverless v2 (~$43/mes de piso por capacidad mínima) o RDS on-demand (~$15/mes) fuera de free tier. |
| Pooling de conexiones | **Supavisor** (pooler nativo de Supabase, basado en PgBouncer) | Cumple el mismo rol que RDS Proxy — evita que las conexiones cortas y concurrentes de Lambda saturen Postgres — pero sin costo adicional ni infraestructura propia que mantener. Se usa la connection string en modo *pooled* (puerto 6543) en lugar de la conexión directa (puerto 5432). |
| Conexión a DB | psycopg2, SQL directo — sin ORM | Con un modelo dimensional fijo y consultas analíticas puntuales, un ORM agrega una capa de abstracción que no aporta valor; SQL directo es más transparente para optimizar y para mostrar dominio del lenguaje en una entrevista. Sin cambios: Supabase es Postgres estándar, por lo que el código de conexión es el mismo que contra RDS. |
| Backend/API | Flask | Framework liviano, foco en ser una capa delgada que sirve JSON sin lógica de negocio (tal como especifica el requisito), sin el overhead de un framework más opinado. |
| Frontend | HTML + CSS + JS vanilla, sin build | El sistema no exige un framework de frontend; vanilla evita la complejidad de un pipeline de build y mantiene el foco del proyecto en la capa de datos y backend. |
| Gráficos | Chart.js | Librería liviana, sin dependencias de build, suficiente para líneas y barras sin necesidad de un ecosistema de visualización más pesado. |
| Mapa | Leaflet + GeoJSON de provincias argentinas | Solución estándar y liviana para mapas interactivos; no requiere claves de API de pago ni SDKs pesados para un mapa coroplético simple. |
| Cómputo backend | **AWS Lambda** (Flask vía adaptador Mangum) con **function URL** | Arquitectura serverless para la API: sin servidor siempre encendido, coherente con un dashboard sin tráfico constante. La function URL es un endpoint HTTPS nativo de Lambda (billing de Lambda, free tier *always free* de 1M requests/mes), reemplaza a API Gateway. El ETL no corre en Lambda (ver fila siguiente); esta fila cubre únicamente el cómputo de la API. Al eliminar RDS/RDS Proxy de la ecuación, tampoco es necesario configurar VPC para Lambda (Supabase se accede por internet público vía Supavisor), lo que simplifica el despliegue. |
| Cómputo ETL | **GitHub Actions** (runner externo, `workflow_dispatch`) | El ETL corre íntegramente en el runner de GitHub Actions, no en AWS. Evita mantener una Lambda adicional (handler, deploy, rol IAM propio) para un proceso que se ejecuta un puñado de veces en la vida del proyecto. Sigue demostrando CI/CD, manejo de secrets y ejecución de un script Python contra la base, sin la fricción operativa de una función serverless dedicada. |
| Hosting frontend | **GitHub Pages** | Hosting gratuito para contenido estático publicado desde el propio repositorio (HTML/CSS/JS sin build), con HTTPS incluido. Reemplaza S3 + CloudFront: cero servicio AWS, cero costo, y el deploy queda atado al repo. Requiere repositorio público (disponible en GitHub Free). Como el sitio vive bajo una subruta (`https://<user>.github.io/<repo>/`), todos los assets usan rutas relativas. |
| Origen del Excel | Versionado en el repositorio (Git) | El dataset es histórico y no cambia entre corridas, por lo que no se justifica un bucket de entrada en S3 ni un mecanismo de descarga externo. El runner de GitHub Actions lo lee directamente del checkout del repo. |
| Automatización de carga | GitHub Actions (`workflow_dispatch`, disparo manual) | El dataset es histórico (no cambia), por lo que programar un cron periódico simularía una necesidad de recurrencia que no existe. Un disparo manual sigue demostrando CI/CD, manejo de secrets y ejecución de un script Python contra la base, sin inventar un caso de uso ficticio. |
| Secrets/config | **Variable de entorno en Lambda + GitHub Secrets** | La connection string de Supabase para el backend se pasa como variable de entorno de la Lambda en el deploy (SAM parámetro `SupabaseDbUrl`, poblado desde un GitHub Secret en `deploy-api.yml`); GitHub Secrets guarda la misma connection string para el workflow de ETL. Ninguna credencial se versiona en el repositorio. Reemplaza a AWS Secrets Manager: para una única connection string en una función propia, una variable de entorno es el cambio más pequeño y no suma un servicio AWS. Como el Excel está versionado en Git (no en S3), el workflow de ETL no necesita credenciales de AWS — solo la connection string de Supabase. |

---

## 4. Arquitectura de deploy (AWS + Supabase)

```
Frontend      → GitHub Pages (hosting estático gratuito, HTTPS, repo público)
Backend       → Lambda (Flask vía Mangum) con function URL
Base de datos → Supabase (PostgreSQL administrado, fuera de AWS)
                  — pooling de conexiones vía Supavisor (incluido, sin costo extra)
ETL/carga     → GitHub Actions (workflow_dispatch, manual), corre el script
                Python sobre el Excel versionado en el repo y carga la base
                usando la connection string de Supabase (GitHub Secrets)
```

### Flujo de datos

1. El script de ETL (Python, disparado manualmente desde GitHub Actions) lee el Excel de origen **versionado en el propio repositorio** (parte del checkout del workflow), lo valida y lo carga al modelo dimensional en Supabase.
2. El backend (Lambda con **function URL**) expone los KPIs y consultas analíticas como endpoints REST, leyendo de Supabase mediante SQL (sin ORM), usando la connection string *pooled* (Supavisor).
3. El frontend, servido estáticamente desde GitHub Pages, hace `fetch()` a los endpoints de la function URL de la Lambda y renderiza las tarjetas de KPIs, el gráfico de líneas, el mapa (Leaflet) y el gráfico de barras (Chart.js). La URL de la API se inyecta en `frontend/js/config.js` (`window.API_BASE`) por el workflow de deploy desde la variable de repo `API_BASE_URL`; en dev local, si `API_BASE` queda vacío, `api.js` cae a `http://127.0.0.1:5000`.
4. El dashboard nunca accede a la base de datos directamente — toda la comunicación pasa por la API.

### Servicios AWS utilizados

- **Lambda** — función de API (Flask vía Mangum) exclusivamente, expuesta con **function URL** (endpoint HTTPS nativo, auth `NONE`, CORS `*`). El ETL no corre en Lambda; se ejecuta en el runner de GitHub Actions (ver sección 5 y fila "Cómputo ETL" en la sección 3).
- **IAM** — rol de la Lambda con permisos de logging únicamente (sin S3 ni Secrets Manager).
- **CloudWatch** — logs de la Lambda (LogGroup con retención de 1 día).
- **AWS Budgets** — alertas de facturación (configurar antes que cualquier otra cosa).

### Fuera de AWS

- **Supabase** — Postgres administrado, reemplaza RDS/Aurora por completo. El modelo dimensional, las consultas SQL y la lógica de carga idempotente se mantienen sin cambios respecto al diseño original.
- **GitHub Pages** — hosting estático del frontend (requiere repositorio público en el plan Free).

### Notas de implementación

- Lambda se conecta a Supabase por la connection string *pooled* (puerto 6543, vía Supavisor), no la conexión directa (puerto 5432) — esto reemplaza la función de RDS Proxy sin costo ni infraestructura adicional.
- Al no depender de RDS, Lambda no necesita correr dentro de una VPC, lo que simplifica el networking y evita cargos de NAT Gateway.
- Ningún archivo de configuración con credenciales se versiona en el repositorio; la connection string de Supabase se inyecta como variable de entorno de la Lambda en el deploy (desde un GitHub Secret via `deploy-api.yml`) y como GitHub Secret para el workflow de ETL. El Excel de origen sí se versiona en el repo — no es una credencial ni un dato sensible, es el dataset de referencia del proyecto.
- El plan free de Supabase pausa proyectos inactivos tras 7 días sin requests. **Mitigación elegida: resumir el proyecto manualmente desde el dashboard de Supabase antes de cada demo.** Se descarta un ping automático programado por ser sobre-ingeniería para un proyecto que se levanta un par de veces en total.
- Configurar una alarma de facturación (AWS Budgets) desde el inicio, incluso con un footprint reducido de Lambda: la capa gratuita de Lambda (function URLs incluidas) es *always free* pero no ilimitada.

---

## 5. Decisiones cerradas

- **Dónde corre el ETL:** GitHub Actions (runner externo), no Lambda dedicada. Justificación: menor infraestructura para mantener, sin restricción de "todo dentro de AWS" que aplique a este caso, y el proyecto se levanta pocas veces (facultad), no en producción continua.
- **De dónde sale el Excel de origen:** versionado en el repositorio, no en un bucket de S3. El runner lo lee directamente del checkout. Esto simplifica permisos (el workflow de ETL solo necesita la connection string de Supabase, sin credenciales de AWS).

## 6. Pendiente de definición

- Estructura de carpetas del repositorio.
- Patrones de diseño puntuales dentro de cada capa (ETL, API, frontend).
- Estrategia de tests automatizados.
- Estrategia de logging/observabilidad del pipeline y de la API.

---

## Apéndice — AWS CLI Setup Guide

### 1. Create IAM User
- IAM Console → Users → Create user
- Attach: `AdministratorAccess` (personal account) or scoped policy
- Generate access key: **Security credentials → Create access key → CLI**

### 2. Install AWS CLI
```bash
# macOS
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o AWSCLIV2.pkg
sudo installer -pkg AWSCLIV2.pkg -target /

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### 3. Configure Credentials
```bash
aws configure
# AWS Access Key ID: <paste>
# AWS Secret Access Key: <paste>
# Default region: us-east-1
# Default output format: json
```

**Alternative (SSO / Identity Center):**
```bash
aws configure sso
```

### 4. Verify Connection
```bash
aws sts get-caller-identity
```

### 5. Named Profiles (multi-account/project)
```bash
aws configure --profile dashboard-project
export AWS_PROFILE=dashboard-project
```

### 6. Secure Credentials File
```bash
chmod 600 ~/.aws/credentials
```
- Never commit `~/.aws/credentials` or `.env` files
- Optional: use `aws-vault` for encrypted key storage

### 7. Billing Safety
- Console → Billing → Budgets → Create budget
- Set alert threshold (e.g. $5)

### 8. Quick Reference — Files
| File | Purpose |
|---|---|
| `~/.aws/credentials` | Access key + secret |
| `~/.aws/config` | Region, output format, profiles |

### 9. Common Commands
```bash
aws configure list                    # show active config
aws configure list-profiles           # list all profiles
aws s3 ls                             # test S3 access
aws lambda list-functions             # test Lambda access
```


























































dashboard-ventas/
│
├── services/
│   │
│   ├── etl/
│   │   ├── src/
│   │   │   └── etl/
│   │   │       ├── __init__.py
│   │   │       ├── extract.py        # lee el Excel con pandas/openpyxl
│   │   │       ├── validate.py       # tipos, nulos, duplicados, contrato de datos
│   │   │       ├── transform.py      # normalización de fechas, año/trim/mes
│   │   │       ├── load.py           # carga idempotente al esquema estrella
│   │   │       └── main.py           # migrate → extract → validate → transform → load
│   │   ├── tests/
│   │   │   ├── test_validate.py
│   │   │   ├── test_transform.py
│   │   │   └── fixtures/
│   │   │       └── ventas_muestra.xlsx
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── api/
│       ├── src/
│       │   └── api/
│       │       ├── __init__.py
│       │       ├── app.py            # Flask app + Mangum handler + CORS + Cache-Control
│       │       ├── routes/
│       │       │   ├── __init__.py
│       │       │   ├── kpis.py       # /kpis/ventas-totales, /kpis/ticket-promedio, etc.
│       │       │   └── analytics.py  # /analytics/top-productos, /analytics/evolucion-mensual
│       │       └── queries/
│       │           ├── kpis_sql.py       # SQL como constantes/funciones, sin ORM
│       │           └── analytics_sql.py
│       ├── tests/
│       │   └── test_routes.py
│       ├── pyproject.toml
│       └── README.md
│
├── packages/
│   └── shared/
│       ├── migrations/
│       ├── src/
│       │   └── shared/
│       │       ├── __init__.py
│       │       ├── db.py             # conexión psycopg2 pooled (Supavisor, puerto 6543)
│       │       ├── schema.py         # nombres de tablas/columnas del modelo dimensional
│       │       └── migrate.py        # runner: aplica migraciones pendientes en orden
│       ├── tests/
│       │   └── test_db.py
│       └── pyproject.toml
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── config.js           # window.API_BASE (inyectado por deploy-frontend.yml; vacío en dev)
│   │   ├── api.js             # fetch a los endpoints, con cache: 'reload' donde aplique
│   │   ├── kpis.js
│   │   ├── chart-lineas.js    # Chart.js — evolución mensual
│   │   ├── chart-barras.js    # Chart.js — rentabilidad por categoría
│   │   └── mapa.js            # Leaflet + GeoJSON
│   └── data/
│       └── geo/provincias.json
│
├── data/
│   └── ventas.xlsx            # dataset versionado en el repo
│
├── infra/
│   ├── template.yaml          # SAM: Lambda con function URL, IAM (logs), variable de entorno SUPABASE_DB_URL
│   └── build.sh               # copia packages/shared/src/shared y services/api/src/api → build dir antes de sam build
│
├── .github/
│   └── workflows/
│       ├── etl.yml            # workflow_dispatch manual; corre migrate.py antes de load
│       ├── deploy-api.yml     # build.sh + sam build/deploy
│       └── deploy-frontend.yml # GitHub Pages: publica frontend/ + inyecta window.API_BASE desde API_BASE_URL
│
├── docs/
│   ├── architecture.md        # este documento + notas de decisiones revisables (FastAPI, trigger ETL)
│   └── data-contract.md       # esquema esperado del Excel de origen
│
├── .gitignore
└── README.md



















































# Modelo Dimensional — Esquema Estrella

## Propósito

Documenta el "por qué" del esquema que implementan las migraciones en `packages/shared/migrations/`. Las migraciones son el DDL ejecutable; este documento es la razón detrás de cada tabla, clave y grano — para que un cambio futuro al esquema se haga con criterio y no reproduciendo `schema.py` a ciegas.

---

## 1. Diagrama entidad-relación

```
                    ┌──────────────────┐
                    │   dim_producto    │
                    ├──────────────────┤
                    │ id_producto (PK)  │
                    │ nombre_producto   │
                    │ categoria         │
                    │ costo             │
                    └────────┬─────────┘
                             │
┌──────────────────┐        │        ┌──────────────────┐
│  dim_sucursal      │        │        │   dim_tiempo       │
├──────────────────┤        │        ├──────────────────┤
│ id_sucursal (PK)   │        │        │ fecha (PK)         │
│ nombre_sucursal    │        │        │ anio               │
│ id_provincia (FK) ─┼──┐     │        │ trimestre          │
└──────────────────┘  │     │        │ mes                 │
                       │     │        └────────┬───────────┘
┌──────────────────┐  │     │                 │
│  dim_provincia     │◄─┘     │                 │
├──────────────────┤        │                 │
│ id_provincia (PK)  │        │                 │
│ nombre_provincia   │        │                 │
└──────────────────┘        │                 │
                             ▼                 ▼
                    ┌───────────────────────────────┐
                    │        fact_ventas             │
                    ├───────────────────────────────┤
                    │ id_ticket (PK, from nro_venta) │
                    │ fecha (FK → dim_tiempo)         │
                    │ id_sucursal (FK → dim_sucursal) │
                    │ id_producto (FK → dim_producto) │
                    │ cantidad                        │
                    │ precio_unitario                 │
                    └───────────────────────────────┘
```

---

## 2. Grano de `fact_ventas`

**Una fila por ticket/venta completa, no por línea de producto.** El origen real (`Hechos_Ventas`) trae una fila por venta con un único producto y su cantidad: `nro_venta` es único. Un ticket con N productos generarían N filas que comparten `id_ticket` — pero ese caso no existe en el dataset actual.

Esto deriva del requisito de datos 2.2: *"Debe existir un identificador de transacción/ticket para no confundir línea de venta con ticket al calcular el Ticket Promedio."* Con grano por ticket, `COUNT(DISTINCT id_ticket)` es equivalente a `COUNT(*)`, y el Ticket Promedio por sucursal se calcula como `SUM(cantidad * precio_unitario) / COUNT(*)` agrupado por sucursal.

**Clave primaria:** `id_ticket` (natural, mapea 1:1 a `nro_venta` del Excel). Es la misma clave natural del contrato de datos (`data-contract.md` §2), no una clave sustituta inventada — mantiene trazabilidad directa al Excel de origen, lo cual ayuda a debuggear discrepancias y habilita el UPSERT idempotente de `data-contract.md` §6.

> Si en el futuro el Excel cambia a grano por línea (varias filas por `nro_venta` con `id_linea`), el PK pasaría a `(id_ticket, id_linea)` — un cambio contenido en `005_create_fact_ventas.sql` y en el contrato.

---

## 3. Dimensiones

### `dim_producto`
Incluye `costo` en la dimensión (no en una tabla de precios separada con vigencia temporal) porque el alcance del proyecto no requiere modelar cambios de costos en el tiempo — es una dimensión de tipo 1 (sobrescritura), no tipo 2 (historización). Si en el futuro se necesitara analizar margen histórico ante cambios de costo, esto pasaría a ser una Slowly Changing Dimension tipo 2, pero eso está fuera del alcance actual.

El origen no trae precio de catálogo (`precio_venta`), solo `costo` y el `precio_unitario` de cada venta. Por eso `dim_producto` guarda únicamente el costo y `fact_ventas.precio_unitario` captura el precio real de venta (que puede diferir por descuento). El Margen Bruto se calcula como `cantidad * (precio_unitario - costo)`.

### `dim_sucursal` y `dim_provincia`
Separadas en dos tablas (en vez de una sola `dim_sucursal` con columna `provincia` de texto libre) para evitar inconsistencias de nombre de provincia entre sucursales distintas (ej. "Buenos Aires" vs. "BUENOS AIRES" en dos filas). `dim_provincia` normaliza el nombre una sola vez; `dim_sucursal` referencia por `id_provincia`. El mapeo de equivalencias mencionado como pendiente en `data-contract.md` §4 se resuelve al momento de poblar `dim_provincia`, no dispersándolo en cada fila de `dim_sucursal`.

Alternativa descartada: desnormalizar `provincia` directo en `dim_sucursal` sin tabla separada. Se descarta porque el requisito 2.2 pide análisis geográfico por provincia como agregación (mapa coroplético), y una tabla `dim_provincia` separada facilita ese `JOIN` y la carga del GeoJSON sin depender de que el texto de provincia esté escrito idénticamente en cada fila de sucursal.

`dim_sucursal.nombre_sucursal` se nutre de la columna `ciudad` del origen (`Dim_Sucursal.ciudad`); la columna `tipo` (Centro/Shopping/Barrio) no se carga por no tener uso en los KPIs definidos.

### `dim_tiempo`
Tabla de fechas explícita (no calcular año/trimestre/mes con funciones SQL en cada consulta) porque el requisito 2.2 pide explícitamente que las fechas *"se normalicen a un formato único que permita derivar año/trimestre/mes"* — materializar esa derivación en una dimensión evita repetir `EXTRACT(QUARTER FROM fecha)` en cada query analítica (`top 5 productos del último trimestre de 2024`, `evolución mensual`) y hace esas consultas más legibles, coherente con el criterio de "SQL directo y legible" ya adoptado para el resto del proyecto.

Clave primaria: `fecha` (tipo `DATE`), no un `id_tiempo` sustituto — no hay necesidad de una superclave numérica cuando la fecha en sí ya es única y ordenable. El origen ya trae un calendario materializado (`Dim_Tiempo` con `id_fecha`, `fecha`, `mes`, `trimestre`, `anio`); el ETL resuelve `Hechos_Ventas.id_fecha → fecha` y carga directamente las derivaciones de origen (no vuelve a calcularlas de cero, solo las valida contra `fecha`). El `id_fecha` origen es un surrogado que no se persiste.

---

## 4. KPIs y su relación con el modelo

| KPI / Consulta | Tablas involucradas | Nota de cálculo |
|---|---|---|
| Ventas Totales | `fact_ventas` | `SUM(cantidad * precio_unitario)` |
| Cantidad Vendida | `fact_ventas` | `SUM(cantidad)` |
| Ticket Promedio por sucursal | `fact_ventas`, `dim_sucursal` | `SUM(cantidad * precio_unitario) / COUNT(*)`, agrupado por `id_sucursal`. Con el grano por ticket de §2, `COUNT(*)` == `COUNT(DISTINCT id_ticket)`. |
| Margen Bruto | `fact_ventas`, `dim_producto` | `SUM(cantidad * (precio_unitario - costo))` — usa `costo` de `dim_producto`, no de `fact_ventas`. |
| Top 5 productos, último trimestre 2024 | `fact_ventas`, `dim_producto`, `dim_tiempo` | Filtro `dim_tiempo.anio = 2024 AND dim_tiempo.trimestre = 4`, agrupado por producto, ordenado por ventas o cantidad. |
| Provincia con mayor volumen | `fact_ventas`, `dim_sucursal`, `dim_provincia` | `JOIN` de las tres tablas, `GROUP BY dim_provincia.nombre_provincia`. |
| Categoría más rentable | `fact_ventas`, `dim_producto` | Margen agrupado por `dim_producto.categoria`. |
| Evolución mensual | `fact_ventas`, `dim_tiempo` | `GROUP BY dim_tiempo.anio, dim_tiempo.mes`. |

Esta tabla es la referencia directa para escribir `services/api/src/api/queries/kpis_sql.py` y `analytics_sql.py` — cada query ahí debería poder señalarse a una fila de esta tabla.

---

## 5. Relación con las migraciones

El orden de `packages/shared/migrations/` sigue la dependencia de claves foráneas de este modelo:

1. `001_create_dim_provincia.sql` — no depende de otras dimensiones, va primero porque `dim_sucursal` la referencia vía FK.
2. `002_create_dim_producto.sql` — no depende de otras dimensiones.
3. `003_create_dim_tiempo.sql` — no depende de otras dimensiones.
4. `004_create_dim_sucursal.sql` — depende de `dim_provincia` (FK `id_provincia`).
5. `005_create_fact_ventas.sql` — al final, porque referencia a las cuatro dimensiones anteriores. `id_ticket` es PK natural (grano por ticket, ver §2).
6. `006_add_fact_ventas_fecha_index.sql` — índice sobre `fact_ventas.fecha`: acelera las consultas que unen por `dim_tiempo` (evolución mensual). El PK de `fact_ventas` (`id_ticket`) ya trae su propio índice.

---

## 6. Pendiente de completar

- ~~Confirmar tipos de dato exactos por columna~~ → **Resuelto en Fase 1** contra el archivo real: `NUMERIC(12,2)` para montos (`costo`, `precio_unitario`), `INTEGER` para ids/cantidad/año/trimestre/mes, `VARCHAR` para cadenas. Reflejado en `packages/shared/migrations/`.
- `dim_producto.categoria` se mantiene como texto plano (sin `dim_categoria` aparte) porque el alcance no pide jerarquía de categorías, solo agrupar por categoría existente.

































































