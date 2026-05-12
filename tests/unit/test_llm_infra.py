"""Tests for the Phase 1 LLM infrastructure."""

from __future__ import annotations

import asyncio
import sqlite3

from ebm_backend.shared.llm.cache import CacheManager
from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.shared.llm.tracker import UsageTracker
from ebm_backend.shared.persistence.db import init_db


class _DummyResponse:
    def __init__(self, content: dict[str, object]):
        self.output_text = "{\"decision\": \"include\"}"
        self._content = content

    def model_dump(self):
        return {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
        }


class _DummyResponses:
    def __init__(self):
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        return _DummyResponse({"decision": "include"})


class _DummyClient:
    def __init__(self):
        self.responses = _DummyResponses()


class _CompatResponses:
    def __init__(self):
        self.calls = 0
        self.seen_text_format = False

    async def create(self, **kwargs):
        self.calls += 1
        if "response_format" in kwargs:
            raise TypeError("AsyncResponses.create() got an unexpected keyword argument 'response_format'")
        if "text" in kwargs:
            self.seen_text_format = True
        return _DummyResponse({"decision": "include"})


class _CompatClient:
    def __init__(self):
        self.responses = _CompatResponses()


class _NotFoundError(Exception):
    status_code = 404


class _ChatMessage:
    def __init__(self, content: str):
        self.content = content


class _ChatChoice:
    def __init__(self, content: str):
        self.message = _ChatMessage(content)


class _ChatResponse:
    def __init__(self, content: str):
        self.choices = [_ChatChoice(content)]

    def model_dump(self):
        return {
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            }
        }


class _MissingResponsesEndpoint:
    async def create(self, **kwargs):
        raise _NotFoundError("Not Found")


class _ChatCompletions:
    def __init__(self):
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        return _ChatResponse("{\"decision\": \"include\"}")


class _Chat:
    def __init__(self):
        self.completions = _ChatCompletions()


class _ChatFallbackClient:
    def __init__(self):
        self.responses = _MissingResponsesEndpoint()
        self.chat = _Chat()


def test_cache_manager_round_trip(tmp_path):
    db_path = tmp_path / "cache.db"
    init_db(f"sqlite:///{db_path}")
    conn = sqlite3.connect(db_path)
    cache = CacheManager(conn)
    key = cache.compute_key("screening", {"study_id": "s1"}, "v1")
    cache.set(
        cache_key=key,
        task_type="screening",
        study_id="s1",
        value_json={"decision": "include"},
        prompt_version="v1",
    )
    assert cache.get(key) == {"decision": "include"}
    stats = cache.get_stats()
    assert stats.total_entries == 1
    assert stats.task_distribution["screening"] == 1


def test_usage_tracker_aggregates(tmp_path):
    db_path = tmp_path / "usage.db"
    init_db(f"sqlite:///{db_path}")
    conn = sqlite3.connect(db_path)
    tracker = UsageTracker(conn)
    tracker.record(
        run_id="run-1",
        module="module_a",
        task_name="task_1",
        model="gpt-5.2",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=25,
    )
    summary = tracker.get_run_summary("run-1")
    assert summary.total_tokens == 150
    assert summary.call_count == 1
    breakdown = tracker.get_module_breakdown("run-1")
    assert breakdown["module_a"].prompt_tokens == 100


def test_gateway_uses_cache_on_second_call(tmp_path):
    db_path = tmp_path / "gateway.db"
    init_db(f"sqlite:///{db_path}")
    conn = sqlite3.connect(db_path)
    client = _DummyClient()
    gateway = LLMGateway(conn=conn, client=client, model="gpt-5.2")
    schema = {"type": "object", "properties": {"decision": {"type": "string"}}, "required": ["decision"]}

    first = asyncio.run(
        gateway.call(
            task_type="screening",
            inputs={"study_id": "s1"},
            prompt_template="Decision: {x}",
            prompt_vars={"x": "include"},
            response_schema=schema,
            study_id="s1",
            task_name="screening_s1",
        )
    )
    second = asyncio.run(
        gateway.call(
            task_type="screening",
            inputs={"study_id": "s1"},
            prompt_template="Decision: {x}",
            prompt_vars={"x": "include"},
            response_schema=schema,
            study_id="s1",
            task_name="screening_s1",
        )
    )

    assert first.cached is False
    assert second.cached is True
    assert client.responses.calls == 1


def test_gateway_fallbacks_to_text_format_when_response_format_unsupported(tmp_path):
    db_path = tmp_path / "gateway_compat.db"
    init_db(f"sqlite:///{db_path}")
    conn = sqlite3.connect(db_path)
    client = _CompatClient()
    gateway = LLMGateway(conn=conn, client=client, model="gpt-5.2")
    schema = {"type": "object", "properties": {"decision": {"type": "string"}}, "required": ["decision"]}

    result = asyncio.run(
        gateway.call(
            task_type="question_expansion",
            inputs={"question": "q"},
            prompt_template="Question: {x}",
            prompt_vars={"x": "q"},
            response_schema=schema,
            cacheable=False,
        )
    )

    assert result.cached is False
    assert result.content == {"decision": "include"}
    assert client.responses.seen_text_format is True
    assert client.responses.calls == 2


def test_gateway_fallbacks_to_chat_completions_when_responses_endpoint_missing(tmp_path):
    db_path = tmp_path / "gateway_chat_fallback.db"
    init_db(f"sqlite:///{db_path}")
    conn = sqlite3.connect(db_path)
    client = _ChatFallbackClient()
    gateway = LLMGateway(conn=conn, client=client, model="gpt-5.2")
    schema = {"type": "object", "properties": {"decision": {"type": "string"}}, "required": ["decision"]}

    result = asyncio.run(
        gateway.call(
            task_type="question_expansion",
            inputs={"question": "q"},
            prompt_template="Question: {x}",
            prompt_vars={"x": "q"},
            response_schema=schema,
            cacheable=False,
        )
    )

    assert result.content == {"decision": "include"}
    assert client.chat.completions.calls == 1
