"""Postgres (Supabase) connection helper. Reads SUPABASE_DB_URL from .env."""
import os
from pathlib import Path

def _load_env():
    p = Path(__file__).with_name(".env")
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

DB_URL = os.environ.get("SUPABASE_DB_URL", "").strip()
DB_PW  = os.environ.get("SUPABASE_DB_PASSWORD", "").strip()

def dsn():
    if not DB_URL:
        raise RuntimeError("SUPABASE_DB_URL not set in backend/.env")
    # Allow storing the URL with the [YOUR-PASSWORD] placeholder from the dashboard
    return DB_URL.replace("[YOUR-PASSWORD]", DB_PW).replace("[PASSWORD]", DB_PW)

def connect():
    import psycopg  # psycopg v3
    return psycopg.connect(dsn(), connect_timeout=15)
