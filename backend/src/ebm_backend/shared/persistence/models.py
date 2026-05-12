"""Database table definitions for the EBM Online pipeline."""

SCHEMA_PIPELINE_RUNS = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    modules_state TEXT,  -- JSONB in PostgreSQL deployments
    final_output TEXT    -- JSONB in PostgreSQL deployments
);
"""

SCHEMA_LLM_CACHE = """
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    study_id TEXT NOT NULL,
    value_json TEXT NOT NULL,  -- JSONB in PostgreSQL deployments
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
    cache_key TEXT,
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
CREATE INDEX IF NOT EXISTS idx_usage_cache_key ON llm_usage(cache_key);
"""

SCHEMA_MODULE1_STUDIES = """
CREATE TABLE IF NOT EXISTS module1_studies (
    study_id TEXT PRIMARY KEY,
    manifest_rel_path TEXT NOT NULL,
    article_path TEXT NOT NULL,
    pmid TEXT,
    pmcid TEXT,
    title TEXT,
    abstract TEXT,
    source TEXT,
    publication_year INTEGER,
    article_type TEXT NOT NULL DEFAULT 'primary_rct',
    open_access BOOLEAN NOT NULL DEFAULT TRUE,
    extraction_status TEXT NOT NULL DEFAULT 'pending',
    extraction_batch_id TEXT,
    extraction_result_json TEXT,
    extraction_error TEXT,
    normalization_status TEXT NOT NULL DEFAULT 'pending',
    normalization_result_json TEXT,
    normalization_error TEXT,
    indexed_status TEXT NOT NULL DEFAULT 'pending',
    indexed_at TIMESTAMP,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_module1_studies_pmid ON module1_studies(pmid);
CREATE INDEX IF NOT EXISTS idx_module1_studies_status ON module1_studies(
    extraction_status, normalization_status, indexed_status
);
"""

SCHEMA_MODULE1_BATCHES = """
CREATE TABLE IF NOT EXISTS module1_batches (
    batch_id TEXT PRIMARY KEY,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    model TEXT NOT NULL,
    input_file_id TEXT,
    output_file_id TEXT,
    error_file_id TEXT,
    request_total INTEGER NOT NULL DEFAULT 0,
    request_completed INTEGER NOT NULL DEFAULT 0,
    request_failed INTEGER NOT NULL DEFAULT 0,
    manifest_path TEXT,
    completion_window TEXT NOT NULL DEFAULT '24h',
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_module1_batches_step ON module1_batches(step_name, status);
"""

ALL_SCHEMAS = [
    SCHEMA_PIPELINE_RUNS,
    SCHEMA_LLM_CACHE,
    SCHEMA_LLM_USAGE,
    SCHEMA_MODULE1_STUDIES,
    SCHEMA_MODULE1_BATCHES,
]
