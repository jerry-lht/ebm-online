"""Database connection and schema initialization."""

import sqlite3
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

from .models import ALL_SCHEMAS


PG_MIGRATIONS = [
    "ALTER TABLE IF EXISTS llm_usage ADD COLUMN IF NOT EXISTS cache_key TEXT;",
]


def get_connection(database_url: str):
    """Create a database connection from a URL."""
    parsed = urlparse(database_url)
    scheme = parsed.scheme
    if scheme.startswith("sqlite"):
        path = parsed.path or ":memory:"
        if path == "/:memory:":
            path = ":memory:"
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path.lstrip("/"),
    )
    conn.autocommit = True
    return conn


def get_dict_cursor(conn):
    """Return a cursor that yields dict-like rows."""
    if isinstance(conn, sqlite3.Connection):
        return conn.cursor()
    return conn.cursor(cursor_factory=RealDictCursor)


def init_db(database_url: str) -> None:
    """Create all tables if they don't exist (idempotent)."""
    conn = get_connection(database_url)
    try:
        if isinstance(conn, sqlite3.Connection):
            cur = conn.cursor()
            for schema in ALL_SCHEMAS:
                cur.executescript(schema)
            conn.commit()
        else:
            with conn.cursor() as cur:
                for migration in PG_MIGRATIONS:
                    cur.execute(migration)
                for schema in ALL_SCHEMAS:
                    cur.execute(schema)
    finally:
        conn.close()
