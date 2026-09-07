import os
from pathlib import Path

import psycopg2

ENV_VAR = "SUPABASE_DB_URL"


def _load_dotenv():
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def database_url():
    _load_dotenv()
    url = os.environ.get(ENV_VAR)
    if not url:
        raise RuntimeError(
            f"{ENV_VAR} no definido. Guardalo en .env en la raíz del repo "
            "(connection string pooled de Supabase, puerto 6543)."
        )
    return url


def connect():
    return psycopg2.connect(database_url())