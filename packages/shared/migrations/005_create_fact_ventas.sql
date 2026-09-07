CREATE TABLE IF NOT EXISTS fact_ventas (
    id_ticket INTEGER PRIMARY KEY,
    fecha DATE NOT NULL REFERENCES dim_tiempo (fecha),
    id_sucursal INTEGER NOT NULL REFERENCES dim_sucursal (id_sucursal),
    id_producto INTEGER NOT NULL REFERENCES dim_producto (id_producto),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12, 2) NOT NULL
);