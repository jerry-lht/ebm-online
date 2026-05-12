"""LLM result cache layer."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Any


CACHEABLE_TASKS = {"screening", "extraction", "rob"}


@dataclass(frozen=True)
class CacheEntry:
    cache_key: str
    task_type: str
    study_id: str
    value_json: dict[str, Any]
    prompt_version: str
    hit_count: int = 0


@dataclass(frozen=True)
class CacheStats:
    total_entries: int
    total_hits: int
    hit_rate: float
    task_distribution: dict[str, int]


class CacheManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def compute_key(task_type: str, inputs: dict[str, Any], prompt_version: str) -> str:
        content = json.dumps(
            {"task_type": task_type, "inputs": inputs, "prompt_version": prompt_version},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_pico_hash(pico: dict[str, Any], eligibility: dict[str, Any]) -> str:
        content = json.dumps(
            {"pico": pico, "eligibility": eligibility},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def is_cacheable(self, task_type: str) -> bool:
        return task_type in CACHEABLE_TASKS

    def get(self, cache_key: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT value_json FROM llm_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if not row:
            return None
        self.conn.execute(
            """
            UPDATE llm_cache
            SET hit_count = hit_count + 1, last_hit_at = CURRENT_TIMESTAMP
            WHERE cache_key = ?
            """,
            (cache_key,),
        )
        self.conn.commit()
        value = row[0]
        return json.loads(value) if isinstance(value, str) else value

    def set(
        self,
        *,
        cache_key: str,
        task_type: str,
        study_id: str,
        value_json: dict[str, Any],
        prompt_version: str,
    ) -> CacheEntry:
        payload = json.dumps(value_json, ensure_ascii=False, sort_keys=True)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO llm_cache (
                cache_key, task_type, study_id, value_json, prompt_version,
                created_at, hit_count, last_hit_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, COALESCE(
                (SELECT hit_count FROM llm_cache WHERE cache_key = ?), 0
            ), (SELECT last_hit_at FROM llm_cache WHERE cache_key = ?))
            """,
            (cache_key, task_type, study_id, payload, prompt_version, cache_key, cache_key),
        )
        self.conn.commit()
        return CacheEntry(
            cache_key=cache_key,
            task_type=task_type,
            study_id=study_id,
            value_json=value_json,
            prompt_version=prompt_version,
        )

    def invalidate_by_study(self, study_id: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM llm_cache WHERE study_id = ?",
            (study_id,),
        )
        self.conn.commit()
        return cur.rowcount

    def invalidate_by_prompt_version(self, task_type: str, old_version: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM llm_cache WHERE task_type = ? AND prompt_version = ?",
            (task_type, old_version),
        )
        self.conn.commit()
        return cur.rowcount

    def invalidate_by_run(self, run_id: str) -> int:
        cur = self.conn.execute(
            """
            DELETE FROM llm_cache
            WHERE cache_key IN (
                SELECT DISTINCT cache_key
                FROM llm_usage
                WHERE run_id = ?
            )
            """,
            (run_id,),
        )
        self.conn.commit()
        return cur.rowcount

    def get_stats(self) -> CacheStats:
        total_entries = self.conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
        total_hits = self.conn.execute("SELECT COALESCE(SUM(hit_count), 0) FROM llm_cache").fetchone()[0]
        rows = self.conn.execute(
            "SELECT task_type, COUNT(*) FROM llm_cache GROUP BY task_type"
        ).fetchall()
        task_distribution = {row[0]: row[1] for row in rows}
        hit_rate = total_hits / total_entries if total_entries else 0.0
        return CacheStats(
            total_entries=total_entries,
            total_hits=total_hits,
            hit_rate=hit_rate,
            task_distribution=task_distribution,
        )
