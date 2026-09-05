# Data Contract — Excel de origen

## Propósito

Este documento especifica el contrato que `services/etl/src/etl/validate.py` debe hacer cumplir. No es una descripción de lo que el Excel *tiene actualmente*, sino de lo que el pipeline *exige* para aceptarlo. Cualquier chequeo en `validate.py` que no derive de una regla explícita en este documento debe considerarse sospechoso — o falta documentar la regla acá, o el chequeo es arbitrario y hay que revisarlo.

Ubicación del archivo: `data/ventas.xlsx`, versionado en el repositorio (ver sección 5 de `architecture.md`).

---

## 1. Hojas esperadas

| Hoja | Contenido | Obligatoria |
|---|---|---|
| `Ventas` | Líneas de venta (grano: una fila por línea de ticket, no por ticket completo) | Sí |
| `Productos` | Catálogo de productos con precio y costo | Sí |
| `Sucursales` | Catálogo de sucursales con provincia asociada | Sí |

Si falta alguna hoja obligatoria o el nombre no coincide exactamente (case-sensitive), el ETL debe abortar antes de procesar cualquier fila — no hay carga parcial de hojas.

---

## 2. Hoja `Ventas`

| Columna | Tipo esperado | Nulo permitido | Regla |
|---|---|---|---|
| `id_ticket` | string/int | No | Identifica el ticket/transacción completo. Múltiples filas pueden compartir el mismo `id_ticket` (una por línea de producto vendido en esa transacción). **Necesario para no confundir línea de venta con ticket al calcular Ticket Promedio** (requisito 2.1 de `architecture.md`). |
| `id_linea` | int | No | Identificador único de la fila dentro del ticket (ej. número de línea). La combinación `(id_ticket, id_linea)` debe ser única — es la clave primaria natural de la hoja. |
| `fecha` | fecha (ver formato origen abajo) | No | Fecha de la venta. Debe caer dentro de un rango razonable (ej. no futura, no anterior a la fecha mínima del dataset conocido). |
| `id_sucursal` | string/int | No | Debe existir en `Sucursales.id_sucursal` (integridad referencial validada antes de cargar). |
| `id_producto` | string/int | No | Debe existir en `Productos.id_producto`. |
| `cantidad` | numérico | No | Debe ser > 0. Cantidad negativa o cero se considera fila inválida (no es una devolución modelada; devoluciones están fuera de alcance según `architecture.md` §2.3). |
| `precio_unitario` | numérico | No | Precio al que se vendió esa línea. Puede diferir del precio de catálogo (`Productos.precio_venta`) por descuentos — no se valida contra el catálogo, se toma como dato de hecho. |

**Formato de fecha en origen:** texto `DD/MM/YYYY`. `transform.py` es responsable de normalizar a `YYYY-MM-DD` (ISO 8601) antes de cargar, de donde se derivan año/trimestre/mes para las consultas analíticas.

**Duplicados:** se considera fila duplicada una repetición exacta de `(id_ticket, id_linea)`. Ante un duplicado, la fila se descarta y se loguea (ver regla de manejo de errores, sección 4).

---

## 3. Hoja `Productos`

| Columna | Tipo esperado | Nulo permitido | Regla |
|---|---|---|---|
| `id_producto` | string/int | No | Clave primaria de la hoja, debe ser único. |
| `nombre_producto` | string | No | — |
| `categoria` | string | No | Usada para la consulta "categoría más rentable". |
| `precio_venta` | numérico | No | > 0. **Necesario para Margen Bruto** (requisito 2.2). |
| `costo` | numérico | No | > 0 y, salvo excepción documentada, `costo < precio_venta` — si aparece un producto con costo mayor al precio de venta, se loguea como advertencia pero no bloquea la carga (puede ser un producto en liquidación real). |

---

## 4. Hoja `Sucursales`

| Columna | Tipo esperado | Nulo permitido | Regla |
|---|---|---|---|
| `id_sucursal` | string/int | No | Clave primaria de la hoja. |
| `nombre_sucursal` | string | No | — |
| `provincia` | string | No | **Necesaria para el análisis geográfico** (requisito 2.2). Debe coincidir con uno de los nombres normalizados de provincia argentina usados en `frontend/data/geo/provincias.json` (ver nota de normalización abajo). |

**Normalización de provincia:** el nombre de provincia en el Excel puede no coincidir textualmente con el `GeoJSON` (ej. "Buenos Aires" vs. "BUENOS AIRES", o "Cordoba" sin tilde vs. "Córdoba"). `transform.py` mapea contra esta tabla de equivalencias fija — es parte de este contrato, no se inventa en el código:

| Valor en Excel | Normalizado | Regla |
|---|---|---|
| `Buenos Aires` | `Buenos Aires` | identidad |
| `Mendoza` | `Mendoza` | identidad |
| `Santa Fe` | `Santa Fe` | identidad |
| `Cordoba` | `Córdoba` | normalización de acento (el GeoJSON estándar de provincias argentinas usa la forma acentuada) |

Cualquier valor de provincia en el Excel que no esté en esta tabla debe abortar la corrida (es un error de contrato, no un caso a inventar).

---

## 5. Manejo de errores de validación

Regla general: **el ETL no debe fallar silenciosamente ni cargar datos parcialmente inconsistentes.**

- **Error bloqueante** (aborta la corrida completa, no carga nada): hoja faltante, columna obligatoria faltante, tipo de dato no coercible (ej. texto no numérico en `cantidad`).
- **Error de fila** (la fila se descarta, la corrida continúa): duplicado de `(id_ticket, id_linea)`, referencia a `id_sucursal`/`id_producto` inexistente, `cantidad <= 0`.
- Todo error de fila debe loguearse con: hoja, número de fila original, columna, valor encontrado, regla violada. El log de la corrida debe quedar accesible como artifact del workflow de GitHub Actions (`etl.yml`).
- **Umbral de aborto:** si más del 5% de las filas de `Ventas` son descartadas por errores de fila, la corrida completa se considera sospechosa y debe abortar en lugar de cargar un dataset silenciosamente degradado. (Valor de umbral sugerido — ajustar si no es razonable para el tamaño real del dataset.)

---

## 6. Idempotencia de la carga

Requisito 2.1 de `architecture.md`: la carga debe ser re-ejecutable sin duplicar ni corromper datos. Esto se resuelve en `load.py`, pero el contrato relevante acá es: `(id_ticket, id_linea)` es la clave estable que permite un `UPSERT` (`INSERT ... ON CONFLICT DO UPDATE`) en `fact_ventas`, en vez de un `INSERT` ciego o un `TRUNCATE` + reload completo.

---

## 7. Pendiente de completar

Ambos huecos que dependían de inspeccionar el Excel real ya están resueltos:

1. ~~Formato exacto de fecha en la hoja `Ventas`.~~ → Texto `DD/MM/YYYY` (ver §2).
2. ~~Tabla de equivalencias de nombres de provincia.~~ → Ver §4.

Si aparecen nuevos valores de provincia o un formato de fecha distinto en una versión futura del Excel, actualizar este documento antes de tocar `validate.py`.