CREATE TABLE IF NOT EXISTS dim_provincia (
    id_provincia INTEGER PRIMARY KEY,
    nombre_provincia VARCHAR(30) NOT NULL UNIQUE
);