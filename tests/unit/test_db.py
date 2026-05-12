"""Tests for database initialization."""

import socket

import pytest

from ebm_backend.shared.persistence.models import ALL_SCHEMAS


def _pg_available():
    """Check if PostgreSQL is reachable on localhost:5432."""
    try:
        sock = socket.create_connection(("localhost", 5432), timeout=1)
        sock.close()
        return True
    except OSError:
        return False


requires_pg = pytest.mark.skipif(
    not _pg_available(), reason="PostgreSQL not available on localhost:5432"
)


def test_schemas_are_valid_sql():
    """Verify all schema strings are non-empty and contain CREATE TABLE."""
    assert len(ALL_SCHEMAS) == 5
    for schema in ALL_SCHEMAS:
        assert "CREATE TABLE IF NOT EXISTS" in schema


def test_schema_defines_pipeline_runs():
    from ebm_backend.shared.persistence.models import SCHEMA_PIPELINE_RUNS

    assert "pipeline_runs" in SCHEMA_PIPELINE_RUNS
    assert "run_id TEXT PRIMARY KEY" in SCHEMA_PIPELINE_RUNS
    assert "JSONB" in SCHEMA_PIPELINE_RUNS


def test_schema_defines_llm_cache():
    from ebm_backend.shared.persistence.models import SCHEMA_LLM_CACHE

    assert "llm_cache" in SCHEMA_LLM_CACHE
    assert "cache_key TEXT PRIMARY KEY" in SCHEMA_LLM_CACHE
    assert "idx_cache_task" in SCHEMA_LLM_CACHE
    assert "idx_cache_study" in SCHEMA_LLM_CACHE


def test_schema_defines_llm_usage():
    from ebm_backend.shared.persistence.models import SCHEMA_LLM_USAGE

    assert "llm_usage" in SCHEMA_LLM_USAGE
    assert "call_id TEXT PRIMARY KEY" in SCHEMA_LLM_USAGE
    assert "idx_usage_run" in SCHEMA_LLM_USAGE


def test_schema_defines_module1_tables():
    from ebm_backend.shared.persistence.models import SCHEMA_MODULE1_BATCHES, SCHEMA_MODULE1_STUDIES

    assert "module1_studies" in SCHEMA_MODULE1_STUDIES
    assert "module1_batches" in SCHEMA_MODULE1_BATCHES
    assert "extraction_status" in SCHEMA_MODULE1_STUDIES
    assert "batch_id TEXT PRIMARY KEY" in SCHEMA_MODULE1_BATCHES


@requires_pg
def test_init_db_creates_tables():
    """Verify init_db creates all three expected tables (requires PostgreSQL)."""
    from ebm_backend.shared.persistence.db import get_connection, init_db

    url = "postgresql://ebm:ebm123@localhost:5432/ebm_online"
    init_db(url)

    conn = get_connection(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            tables = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    assert "pipeline_runs" in tables
    assert "llm_cache" in tables
    assert "llm_usage" in tables


@requires_pg
def test_init_db_is_idempotent():
    """Running init_db twice should not raise errors."""
    from ebm_backend.shared.persistence.db import init_db

    url = "postgresql://ebm:ebm123@localhost:5432/ebm_online"
    init_db(url)
    init_db(url)
