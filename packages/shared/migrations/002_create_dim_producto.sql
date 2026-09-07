CREATE TABLE IF NOT EXISTS dim_producto (
    id_producto INTEGER PRIMARY KEY,
    nombre_producto VARCHAR(50) NOT NULL,
    categoria VARCHAR(20) NOT NULL,
    costo NUMERIC(12, 2) NOT NULL
);