"""Unified LLM call interface with caching and tracking."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Any

try:
    from openai import AsyncOpenAI
except ModuleNotFoundError:  # pragma: no cover - optional during unit tests
    AsyncOpenAI = Any  # type: ignore[assignment]

from ebm_backend.shared.config.settings import settings
from ebm_backend.shared.llm.cache import CacheManager
from ebm_backend.shared.llm.tracker import TokenUsage, UsageTracker, usage_from_payload


@dataclass(frozen=True)
class LLMResult:
    content: dict[str, Any]
    raw_response: str
    usage: TokenUsage
    cached: bool
    latency_ms: int
    call_id: str


@dataclass(frozen=True)
class LLMRequest:
    task_type: str
    inputs: dict[str, Any]
    prompt_template: str
    prompt_vars: dict[str, Any]
    response_schema: dict[str, Any]
    temperature: float = 0.0
    cacheable: bool = True
    run_id: str | None = None
    module: str = "shared"
    task_name: str = "task"
    study_id: str = "unknown"
    prompt_version: str = "v1"


@dataclass(frozen=True)
class _ResponseAdapter:
    output_text: str
    raw_payload: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return self.raw_payload


class LLMGateway:
    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        client: AsyncOpenAI | None = None,
        model: str | None = None,
    ):
        self.conn = conn
        self.cache = CacheManager(conn) if conn is not None else None
        self.tracker = UsageTracker(conn) if conn is not None else None
        if client is None and not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for real LLM execution.")
        self.client = client or AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "180")),
        )
        self.model = model or settings.llm_model

    async def call(
        self,
        task_type: str,
        inputs: dict[str, Any],
        prompt_template: str,
        prompt_vars: dict[str, Any],
        response_schema: dict[str, Any],
        temperature: float = 0,
        cacheable: bool = True,
        run_id: str | None = None,
        module: str = "shared",
        task_name: str = "task",
        study_id: str = "unknown",
        prompt_version: str = "v1",
    ) -> LLMResult:
        request = LLMRequest(
            task_type=task_type,
            inputs=inputs,
            prompt_template=prompt_template,
            prompt_vars=prompt_vars,
            response_schema=response_schema,
            temperature=temperature,
            cacheable=cacheable,
            run_id=run_id,
            module=module,
            task_name=task_name,
            study_id=study_id,
            prompt_version=prompt_version,
        )
        cache_key = CacheManager.compute_key(task_type, inputs, prompt_version)
        if cacheable and self.cache is not None and self.cache.is_cacheable(task_type):
            cached = self.cache.get(cache_key)
            if cached is not None:
                call_id = str(uuid.uuid4())
                usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
                if self.tracker is not None:
                    self.tracker.record(
                        run_id=run_id,
                        module=module,
                        task_name=task_name,
                        cache_key=cache_key,
                        model=self.model,
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=0,
                        cached=True,
                        success=True,
                        call_id=call_id,
                    )
                return LLMResult(
                    content=cached,
                    raw_response=json.dumps(cached, ensure_ascii=False),
                    usage=usage,
                    cached=True,
                    latency_ms=0,
                    call_id=call_id,
                )

        start = time.perf_counter()
        response = await self._create_structured_response(
            task_type=task_type,
            prompt=self._build_prompt(prompt_template, prompt_vars),
            response_schema=response_schema,
            temperature=temperature,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        raw_response = response.output_text or ""
        content = self._parse_json(raw_response)
        usage = usage_from_payload(response.model_dump())
        call_id = str(uuid.uuid4())
        if cacheable and self.cache is not None and self.cache.is_cacheable(task_type):
            self.cache.set(
                cache_key=cache_key,
                task_type=task_type,
                study_id=study_id,
                value_json=content,
                prompt_version=prompt_version,
            )
        if self.tracker is not None:
            self.tracker.record(
                run_id=run_id,
                module=module,
                task_name=task_name,
                cache_key=cache_key,
                model=self.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                latency_ms=latency_ms,
                cached=False,
                success=True,
                call_id=call_id,
            )
        return LLMResult(
            content=content,
            raw_response=raw_response,
            usage=usage,
            cached=False,
            latency_ms=latency_ms,
            call_id=call_id,
        )

    async def call_batch(self, requests: list[LLMRequest]) -> list[LLMResult]:
        return await asyncio.gather(*(self.call(**request.__dict__) for request in requests))

    def build_batch_input(self, requests: list[LLMRequest]) -> str:
        lines: list[str] = []
        for request in requests:
            body = {
                "model": self.model,
                "input": self._build_prompt(request.prompt_template, request.prompt_vars),
                "temperature": request.temperature,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": request.task_type,
                        "schema": request.response_schema,
                        "strict": True,
                    },
                },
            }
            lines.append(
                json.dumps(
                    {
                        "custom_id": f"{request.study_id}:{request.task_type}",
                        "method": "POST",
                        "url": "/v1/responses",
                        "body": body,
                    },
                    ensure_ascii=False,
                )
            )
        return "\n".join(lines)

    async def create_batch_job(
        self,
        *,
        requests: list[LLMRequest],
        completion_window: str = "24h",
    ) -> dict[str, Any]:
        if not hasattr(self.client, "files") or not hasattr(self.client, "batches"):
            raise RuntimeError("Batch API requires an OpenAI client with files and batches support")
        input_payload = self.build_batch_input(requests)
        temp_path = f"/tmp/{uuid.uuid4().hex}.jsonl"
        with open(temp_path, "w", encoding="utf-8") as fh:
            fh.write(input_payload)
        try:
            with open(temp_path, "rb") as fh:
                uploaded = await self.client.files.create(file=fh, purpose="batch")
            batch = await self.client.batches.create(
                input_file_id=uploaded.id,
                endpoint="/v1/responses",
                completion_window=completion_window,
            )
            return {
                "batch_id": batch.id,
                "input_file_id": uploaded.id,
                "status": batch.status,
                "raw": batch.model_dump() if hasattr(batch, "model_dump") else batch,
            }
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    async def poll_batch(self, batch_id: str) -> dict[str, Any]:
        batch = await self.client.batches.retrieve(batch_id)
        return batch.model_dump() if hasattr(batch, "model_dump") else batch

    async def fetch_batch_output(self, output_file_id: str) -> list[dict[str, Any]]:
        file_content = await self.client.files.content(output_file_id)
        raw = file_content.read() if hasattr(file_content, "read") else file_content
        if isinstance(raw, bytes):
            raw_text = raw.decode("utf-8")
        else:
            raw_text = str(raw)
        records = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
        return records

    @staticmethod
    def _build_prompt(prompt_template: str, prompt_vars: dict[str, Any]) -> str:
        try:
            return prompt_template.format(**prompt_vars)
        except KeyError:
            return prompt_template

    @staticmethod
    def _parse_json(raw_response: str) -> dict[str, Any]:
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response was not valid JSON") from exc

    async def _create_structured_response(
        self,
        *,
        task_type: str,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float,
    ):
        if self._prefer_chat_completions() and hasattr(self.client, "chat") and hasattr(self.client.chat, "completions"):
            return await self._create_chat_structured_response(
                task_type=task_type,
                prompt=prompt,
                response_schema=response_schema,
                temperature=temperature,
            )
        schema_payload = {
            "type": "json_schema",
            "json_schema": {
                "name": task_type,
                "schema": response_schema,
                "strict": True,
            },
        }
        request_variants = [
            {"response_format": schema_payload},
            {
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": task_type,
                        "schema": response_schema,
                        "strict": True,
                    }
                }
            },
        ]
        last_exc: Exception | None = None
        for extra_kwargs in request_variants:
            try:
                return await self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    temperature=temperature,
                    **extra_kwargs,
                )
            except TypeError as exc:
                last_exc = exc
                message = str(exc)
                if "unexpected keyword argument" in message:
                    continue
                raise
            except Exception as exc:
                last_exc = exc
                if self._is_not_found_error(exc):
                    break
                raise
        if hasattr(self.client, "chat") and hasattr(self.client.chat, "completions"):
            return await self._create_chat_structured_response(
                task_type=task_type,
                prompt=prompt,
                response_schema=response_schema,
                temperature=temperature,
            )
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Failed to create structured response.")

    async def _create_chat_structured_response(
        self,
        *,
        task_type: str,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float,
    ) -> _ResponseAdapter:
        schema_payload = {
            "type": "json_schema",
            "json_schema": {
                "name": task_type,
                "schema": response_schema,
                "strict": True,
            },
        }
        prompt_with_schema = (
            f"{prompt}\n\nReturn only valid JSON matching this JSON Schema:\n"
            f"{json.dumps(response_schema, ensure_ascii=False)}"
        )
        request_variants = [
            {
                "messages": [{"role": "user", "content": prompt}],
                "response_format": schema_payload,
            },
            {
                "messages": [{"role": "user", "content": prompt_with_schema}],
                "response_format": {"type": "json_object"},
            },
        ]
        last_exc: Exception | None = None
        for extra_kwargs in request_variants:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    temperature=temperature,
                    **extra_kwargs,
                )
                raw_payload = response.model_dump() if hasattr(response, "model_dump") else {}
                output_text = self._extract_chat_output_text(response)
                return _ResponseAdapter(output_text=output_text, raw_payload=raw_payload)
            except TypeError as exc:
                last_exc = exc
                if "unexpected keyword argument" in str(exc):
                    continue
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Failed to create structured chat response.")

    @staticmethod
    def _extract_chat_output_text(response: Any) -> str:
        choices = getattr(response, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if content:
                return content
        if isinstance(response, dict):
            return str(response["choices"][0]["message"]["content"])
        return ""

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        return getattr(exc, "status_code", None) == 404 or exc.__class__.__name__.endswith("NotFoundError")

    @staticmethod
    def _prefer_chat_completions() -> bool:
        if os.getenv("LLM_FORCE_CHAT_COMPLETIONS") == "1":
            return True
        base_url = str(settings.openai_base_url or "")
        host = urlparse(base_url).netloc.lower()
        return host.endswith("siliconflow.cn")
