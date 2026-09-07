from pathlib import Path

from shared.db import connect
from shared.schema import MIGRATIONS_TABLE

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

_DDL = f"""
CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def _applied(conn):
    with conn.cursor() as cur:
        cur.execute(f"SELECT filename FROM {MIGRATIONS_TABLE}")
        return {row[0] for row in cur.fetchall()}


def migrate():
    files = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(_DDL)
        conn.commit()
        done = _applied(conn)
        for filename in files:
            if filename in done:
                continue
            sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    f"INSERT INTO {MIGRATIONS_TABLE} (filename) VALUES (%s)",
                    (filename,),
                )
            conn.commit()
            print(f"applied {filename}")
        print(f"total {len(files)}, nuevas {len(files) - len(done)}, previas {len(done)}")


if __name__ == "__main__":
    migrate()