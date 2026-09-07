import os

import pytest

from shared.db import connect
from shared.migrate import MIGRATIONS_DIR, migrate
from shared.schema import (
    MIGRATIONS_TABLE,
    TABLE_DIM_PRODUCTO,
    TABLE_DIM_PROVINCIA,
    TABLE_DIM_SUCURSAL,
    TABLE_DIM_TIEMPO,
    TABLE_FACT_VENTAS,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_DB_URL"),
    reason="SUPABASE_DB_URL no definido",
)

ALL_TABLES = {
    TABLE_DIM_PROVINCIA,
    TABLE_DIM_PRODUCTO,
    TABLE_DIM_TIEMPO,
    TABLE_DIM_SUCURSAL,
    TABLE_FACT_VENTAS,
}


@pytest.fixture(scope="module")
def conn():
    c = connect()
    yield c
    c.close()


def test_connect(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1


def test_migrations_applied(conn):
    expected = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))
    with conn.cursor() as cur:
        cur.execute(f"SELECT filename FROM {MIGRATIONS_TABLE} ORDER BY filename")
        applied = [row[0] for row in cur.fetchall()]
    assert applied == expected


def test_migrate_idempotent(conn):
    with conn.cursor() as cur:
        cur.execute(f"SELECT filename FROM {MIGRATIONS_TABLE} ORDER BY filename")
        before = [row[0] for row in cur.fetchall()]
    migrate()
    with conn.cursor() as cur:
        cur.execute(f"SELECT filename FROM {MIGRATIONS_TABLE} ORDER BY filename")
        after = [row[0] for row in cur.fetchall()]
    assert before == after


def test_star_schema_tables_exist(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        present = {row[0] for row in cur.fetchall()}
    assert ALL_TABLES <= present


def test_fact_ventas_pk_y_fks(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT kcu.column_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "ON tc.constraint_name = kcu.constraint_name "
            "WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY'",
            (TABLE_FACT_VENTAS,),
        )
        assert [r[0] for r in cur.fetchall()] == ["id_ticket"]
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.table_constraints "
            "WHERE table_name = %s AND constraint_type = 'FOREIGN KEY'",
            (TABLE_FACT_VENTAS,),
        )
        assert cur.fetchone()[0] == 3


def test_fact_ventas_fecha_index(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM pg_indexes "
            "WHERE tablename = %s AND indexname = 'idx_fact_ventas_fecha'",
            (TABLE_FACT_VENTAS,),
        )
        assert cur.fetchone()[0] == 1


def test_tipos_de_dato(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = 'precio_unitario'",
            (TABLE_FACT_VENTAS,),
        )
        assert cur.fetchone()[0] == "numeric"
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = 'id_ticket'",
            (TABLE_FACT_VENTAS,),
        )
        assert cur.fetchone()[0] == "integer"
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = 'costo'",
            (TABLE_DIM_PRODUCTO,),
        )
        assert cur.fetchone()[0] == "numeric"