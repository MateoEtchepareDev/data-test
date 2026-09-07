CREATE TABLE IF NOT EXISTS dim_sucursal (
    id_sucursal INTEGER PRIMARY KEY,
    nombre_sucursal VARCHAR(30) NOT NULL,
    id_provincia INTEGER NOT NULL REFERENCES dim_provincia (id_provincia)
);