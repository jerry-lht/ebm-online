"""PostgreSQL database connection and schema initialization."""

from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

from .models import ALL_SCHEMAS


def get_connection(database_url: str):
    """Create a PostgreSQL connection from a URL."""
    parsed = urlparse(database_url)
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
    return conn.cursor(cursor_factory=RealDictCursor)


def init_db(database_url: str) -> None:
    """Create all tables if they don't exist (idempotent)."""
    conn = get_connection(database_url)
    try:
        with conn.cursor() as cur:
            for schema in ALL_SCHEMAS:
                cur.execute(schema)
    finally:
        conn.close()
