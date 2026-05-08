"""Database table definitions for the EBM Online pipeline (PostgreSQL)."""

SCHEMA_PIPELINE_RUNS = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    modules_state JSONB,
    final_output JSONB
);
"""

SCHEMA_LLM_CACHE = """
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    study_id TEXT NOT NULL,
    value_json JSONB NOT NULL,
    prompt_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cache_task ON llm_cache(task_type);
CREATE INDEX IF NOT EXISTS idx_cache_study ON llm_cache(study_id);
CREATE INDEX IF NOT EXISTS idx_cache_prompt ON llm_cache(task_type, prompt_version);
"""

SCHEMA_LLM_USAGE = """
CREATE TABLE IF NOT EXISTS llm_usage (
    call_id TEXT PRIMARY KEY,
    run_id TEXT,
    module TEXT NOT NULL,
    task_name TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'gpt-5.2',
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    cached BOOLEAN NOT NULL DEFAULT FALSE,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_run ON llm_usage(run_id);
CREATE INDEX IF NOT EXISTS idx_usage_module ON llm_usage(module);
"""

ALL_SCHEMAS = [SCHEMA_PIPELINE_RUNS, SCHEMA_LLM_CACHE, SCHEMA_LLM_USAGE]
