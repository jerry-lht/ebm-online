"""Token consumption and cost tracking."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from ebm_backend.shared.llm.pricing import calculate_cost


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class UsageRecord:
    call_id: str
    run_id: str | None
    module: str
    task_name: str
    cache_key: str | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    cached: bool
    success: bool
    timestamp: str | None = None


@dataclass(frozen=True)
class RunUsageSummary:
    run_id: str
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    total_latency_ms: int
    call_count: int


@dataclass(frozen=True)
class ModuleUsage:
    module: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    call_count: int


@dataclass(frozen=True)
class DailyCost:
    day: str
    cost_usd: float


class UsageTracker:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def record(
        self,
        *,
        run_id: str | None,
        module: str,
        task_name: str,
        cache_key: str | None = None,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        cached: bool = False,
        success: bool = True,
        call_id: str | None = None,
    ) -> UsageRecord:
        call_id = call_id or str(uuid.uuid4())
        total_tokens = prompt_tokens + completion_tokens
        cost = 0.0 if cached else calculate_cost(model, prompt_tokens, completion_tokens)
        self.conn.execute(
            """
            INSERT INTO llm_usage (
                call_id, run_id, module, task_name, model,
                cache_key,
                prompt_tokens, completion_tokens, total_tokens,
                cost_usd, latency_ms, cached, success
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                run_id,
                module,
                task_name,
                model,
                cache_key,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost,
                latency_ms,
                int(cached),
                int(success),
            ),
        )
        self.conn.commit()
        return UsageRecord(
            call_id=call_id,
            run_id=run_id,
            module=module,
            task_name=task_name,
            cache_key=cache_key,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            cached=cached,
            success=success,
        )

    def get_run_summary(self, run_id: str) -> RunUsageSummary:
        row = self.conn.execute(
            """
            SELECT
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COALESCE(SUM(cost_usd), 0.0) AS cost_usd,
                COALESCE(SUM(latency_ms), 0) AS latency_ms,
                COUNT(*) AS call_count
            FROM llm_usage
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        return RunUsageSummary(
            run_id=run_id,
            total_prompt_tokens=row[0],
            total_completion_tokens=row[1],
            total_tokens=row[2],
            total_cost_usd=row[3],
            total_latency_ms=row[4],
            call_count=row[5],
        )

    def get_module_breakdown(self, run_id: str) -> dict[str, ModuleUsage]:
        rows = self.conn.execute(
            """
            SELECT
                module,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COALESCE(SUM(cost_usd), 0.0) AS cost_usd,
                COALESCE(SUM(latency_ms), 0) AS latency_ms,
                COUNT(*) AS call_count
            FROM llm_usage
            WHERE run_id = ?
            GROUP BY module
            """,
            (run_id,),
        ).fetchall()
        return {
            row[0]: ModuleUsage(
                module=row[0],
                prompt_tokens=row[1],
                completion_tokens=row[2],
                total_tokens=row[3],
                cost_usd=row[4],
                latency_ms=row[5],
                call_count=row[6],
            )
            for row in rows
        }

    def get_cost_trend(self, days: int = 30) -> list[DailyCost]:
        rows = self.conn.execute(
            """
            SELECT substr(timestamp, 1, 10) AS day, COALESCE(SUM(cost_usd), 0.0) AS cost_usd
            FROM llm_usage
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (days,),
        ).fetchall()
        return [DailyCost(day=row[0], cost_usd=row[1]) for row in rows]


def usage_from_payload(payload: dict[str, Any]) -> TokenUsage:
    usage = payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
