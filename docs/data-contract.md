# Data Contract — Excel de origen

## Propósito

Este documento especifica el contrato que `services/etl/src/etl/validate.py` debe hacer cumplir. No es una descripción de lo que el Excel *tiene actualmente*, sino de lo que el pipeline *exige* para aceptarlo. Cualquier chequeo en `validate.py` que no derive de una regla explícita en este documento debe considerarse sospechoso — o falta documentar la regla acá, o el chequeo es arbitrario y hay que revisarlo.

La versión actual del contrato fue alineada contra el archivo real `data/ventas.xlsx` (hojas, grano y tipos de dato verificados) en Fase 1, a diferencia de los borradores previos que describían un Excel hipotético.

Ubicación del archivo: `data/ventas.xlsx`, versionado en el repositorio (ver `architecture.md` §5).

---

## 1. Hojas esperadas

| Hoja | Contenido | Obligatoria |
|---|---|---|
| `Hechos_Ventas` | Líneas de venta (grano: una fila por ticket/venta, no por línea de producto) | Sí |
| `Dim_Producto` | Catálogo de productos con costo | Sí |
| `Dim_Sucursal` | Catálogo de sucursales con provincia asociada | Sí |
| `Dim_Tiempo` | Calendario: `id_fecha` → `fecha` + año/trimestre/mes derivados | Sí |

Si falta alguna hoja obligatoria o el nombre no coincide exactamente (case-sensitive), el ETL debe abortar antes de procesar cualquier fila — no hay carga parcial de hojas.

---

## 2. Hoja `Hechos_Ventas`

| Columna | Tipo esperado | Nulo permitido | Regla |
|---|---|---|---|
| `nro_venta` | int | No | Identificador único del ticket/venta completo. Una fila por ticket. **Necesario para no confundir línea de venta con ticket al calcular Ticket Promedio** (requisito 2.1 de `architecture.md`). |
| `id_fecha` | int | No | Referencia a `Dim_Tiempo.id_fecha`. Debe existir (integridad referencial validada antes de cargar). |
| `id_producto` | int | No | Debe existir en `Dim_Producto.id_producto`. |
| `id_sucursal` | int | No | Debe existir en `Dim_Sucursal.id_sucursal`. |
| `cantidad` | int | No | Debe ser > 0. Cantidad negativa o cero se considera fila inválida (no es una devolución modelada; devoluciones están fuera de alcance según `architecture.md` §2.3). |
| `precio_unitario` | numérico | No | Precio al que se vendió esa línea. No se valida contra un "precio de catálogo" (no existe en el origen); se toma como dato de hecho. |
| `total` | numérico | No | `cantidad * precio_unitario`. Si no coincide, se loguea advertencia pero no bloquea cargo (derivable, se usa más como sanity check). |

**Formato de fecha en origen:** la hoja no expone una fecha en texto; la fecha vive en `Dim_Tiempo` como tipo `DATE` real (ISO 8601, sin hora). `transform.py` resuelve `id_fecha → fecha` y deriva año/trimestre/mes para el modelo.

**Duplicados:** se considera fila duplicada una repetición exacta de `nro_venta`. Ante un duplicado, la fila se descarta y se loguea (ver regla de manejo de errores, sección 5).

---

## 3. Hoja `Dim_Producto`

| Columna | Tipo esperado | Nulo permitido | Regla |
|---|---|---|---|
| `id_producto` | int | No | Clave primaria de la hoja, debe ser único. |
| `nombre` | string | No | — |
| `categoria` | string | No | Usada para la consulta "categoría más rentable". |
| `costo` | numérico | No | > 0. Si `costo` supera el `precio_unitario` de alguna venta del producto, se loguea como advertencia pero no bloquea la carga (puede ser un producto en liquidación real). |

Nota: el origen **no trae** un precio de catálogo (`precio_venta`). El margen bruto se calcula contra `fact_ventas.precio_unitario` (precio de venta real) y `dim_producto.costo`.

---

## 4. Hojas `Dim_Sucursal` y `Dim_Tiempo`

### `Dim_Sucursal`

| Columna | Tipo esperado | Nulo permitido | Regla |
|---|---|---|---|
| `id_sucursal` | int | No | Clave primaria de la hoja. |
| `ciudad` | string | No | Ciudad de la sucursal; alimenta `dim_sucursal.nombre_sucursal`. |
| `provincia` | string | No | **Necesaria para el análisis geográfico** (requisito 2.2). Debe coincidir con uno de los nombres normalizados de provincia argentina usados en `frontend/data/geo/provincias.json` (ver nota de normalización abajo). |
| `tipo` | string | No | No se carga al modelo (solo `id_sucursal`, `ciudad`, `provincia`). No tiene uso en los KPIs definidos. |

### `Dim_Tiempo`

| Columna | Tipo esperado | Nulo permitido | Regla |
|---|---|---|---|
| `id_fecha` | int | No | Clave primaria de la hoja; referenciada por `Hechos_Ventas.id_fecha`. |
| `fecha` | fecha (DATE) | No | Fecha de venta, formato ISO, sin hora. Debe ser única. |
| `dia` | int | No | 1–31. No se carga al modelo (derivable de `fecha`). |
| `mes` | int | No | 1–12. |
| `trimestre` | int | No | 1–4. |
| `anio` | int | No | — |

**Normalización de provincia:** el primer dataset real ya trae las provincias acentuadas (`Córdoba`, `Buenos Aires`, etc.), por lo que la tabla de equivalencias siguiente es identidad para los valores conocidos — pero sigue siendo el contrato: cualquier valor de provincia en el Excel que no esté en esta tabla debe abortar la corrida (es un error de contrato, no un caso a inventar). `transform.py` aplica el mapa por robustez, no por necesidad actual:

| Valor en Excel | Normalizado | Regla |
|---|---|---|
| `Buenos Aires` | `Buenos Aires` | identidad |
| `Córdoba` | `Córdoba` | identidad (el Excel actual ya viene acentuado) |
| `Mendoza` | `Mendoza` | identidad |
| `Santa Fe` | `Santa Fe` | identidad |

---

## 5. Manejo de errores de validación

Regla general: **el ETL no debe fallar silenciosamente ni cargar datos parcialmente inconsistentes.**

- **Error bloqueante** (aborta la corrida completa, no carga nada): hoja faltante, columna obligatoria faltante, tipo de dato no coercible (ej. texto no numérico en `cantidad`).
- **Error de fila** (la fila se descarta, la corrida continúa): duplicado de `nro_venta`, referencia a `id_sucursal`/`id_producto`/`id_fecha` inexistente, `cantidad <= 0`.
- Todo error de fila debe loguearse con: hoja, número de fila original, columna, valor encontrado, regla violada. El log de la corrida debe quedar accesible como artifact del workflow de GitHub Actions (`etl.yml`).
- **Umbral de aborto:** si más del 5% de las filas de `Hechos_Ventas` son descartadas por errores de fila, la corrida completa se considera sospechosa y debe abortar en lugar de cargar un dataset silenciosamente degradado. (Valor de umbral sugerido — ajustar si no es razonable para el tamaño real del dataset.)

---

## 6. Idempotencia de la carga

Requisito 2.1 de `architecture.md`: la carga debe ser re-ejecutable sin duplicar ni corromper datos. Esto se resuelve en `load.py`, pero el contrato relevante acá es: `nro_venta` es la clave estable que permite un `UPSERT` (`INSERT ... ON CONFLICT (id_ticket) DO UPDATE`) en `fact_ventas`, en vez de un `INSERT` ciego o un `TRUNCATE` + reload completo. Las dimensiones cargan por su clave natural (`id_producto`, `id_sucursal`, `fecha`, `nombre_provincia`).

---

## 7. Notas de versión del contrato

- El grano del origen es **por ticket** (`nro_venta` único), no por línea. No existe `id_linea`. Ver `architecture.md` "Grano de `fact_ventas`".
- La fecha no viene como texto `DD/MM/YYYY` sino como `DATE` desde `Dim_Tiempo` (resuelta vía `id_fecha`).
- Si aparecen nuevos valores de provincia, un formato de fecha distinto, o un cambio de grano en una versión futura del Excel, actualizar este documento antes de tocar `validate.py`.