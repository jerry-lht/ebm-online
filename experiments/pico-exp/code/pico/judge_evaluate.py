"""LLM-judge rubric evaluation for PICO text predictions."""

from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pico.prompt_registry import read_prompt_template
from pico.schemas import DocumentExample, PICO_LABELS

JUDGE_EVALUATOR_VERSION = "phase9-judge-v1"
JUDGE_PROMPT_VERSION = "judge_rubric_v2"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_WORKERS = 16
DEFAULT_MAX_RETRIES = 2

COMPLETENESS_VALUES: tuple[str, ...] = ("complete", "partial", "missing")
ACCURACY_VALUES: tuple[str, ...] = ("accurate", "mixed", "incorrect")
NOISE_VALUES: tuple[str, ...] = ("low", "medium", "high")
GRANULARITY_VALUES: tuple[str, ...] = ("appropriate", "too_broad", "too_narrow", "mixed")
VERDICT_VALUES: tuple[str, ...] = ("strong", "mixed", "weak")
DIMENSION_VALUES: dict[str, tuple[str, ...]] = {
    "completeness": COMPLETENESS_VALUES,
    "accuracy": ACCURACY_VALUES,
    "noise": NOISE_VALUES,
    "granularity": GRANULARITY_VALUES,
    "overall_verdict": VERDICT_VALUES,
}


@dataclass(frozen=True)
class JudgeInput:
    doc_id: str
    abstract: str
    gold: dict[str, list[str]]
    predicted: dict[str, list[str]]


@dataclass(frozen=True)
class JudgeFailure:
    doc_id: str
    error_type: str
    message: str


def build_judge_inputs(
    examples: list[DocumentExample],
    raw_rows: list[dict[str, Any]],
) -> tuple[list[JudgeInput], dict[str, Any]]:
    """Build per-document judge payloads from gold examples and raw text predictions."""
    predictions_by_doc, prediction_quality = _aggregate_predictions(raw_rows)
    judge_inputs: list[JudgeInput] = []
    for example in examples:
        gold = {label: [] for label in PICO_LABELS}
        for span in example.gold_spans:
            if span.label in gold:
                gold[span.label].append(span.text)
        predicted = predictions_by_doc.get(example.doc_id)
        if predicted is None:
            predicted = {label: [] for label in PICO_LABELS}
        judge_inputs.append(
            JudgeInput(
                doc_id=example.doc_id,
                abstract=example.abstract,
                gold=gold,
                predicted=predicted,
            )
        )
    prediction_quality["docs_with_gold"] = len(examples)
    prediction_quality["docs_with_prediction_row"] = len(predictions_by_doc)
    return judge_inputs, prediction_quality


def run_llm_judge(
    judge_inputs: list[JudgeInput],
    *,
    provider: str,
    model_id: str,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    workers: int = DEFAULT_WORKERS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    api_mode: str = "responses",
    prompt_version: str = JUDGE_PROMPT_VERSION,
    show_progress: bool = False,
) -> list[dict[str, Any]]:
    """Run rubric judge for each document and return row-wise JSONL results plus failures."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    if not judge_inputs:
        return [], []

    prompt_template = _read_prompt_template(prompt_version)
    progress = _ProgressPrinter(total=len(judge_inputs), enabled=show_progress)
    rows_by_doc_id: dict[str, dict[str, Any]] = {}
    failures: list[JudgeFailure] = []

    max_workers = min(workers, max(1, len(judge_inputs)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _judge_single_input,
                judge_input=judge_input,
                provider=provider,
                model_id=model_id,
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                api_mode=api_mode,
                prompt_template=prompt_template,
                prompt_version=prompt_version,
                max_retries=max_retries,
            ): judge_input.doc_id
            for judge_input in judge_inputs
        }
        for future in concurrent.futures.as_completed(futures):
            doc_id = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                failures.append(
                    JudgeFailure(
                        doc_id=doc_id,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
                progress.failed(doc_id=doc_id, message=str(exc))
                continue
            rows_by_doc_id[doc_id] = row
            progress.done(doc_id=doc_id)

    progress.finish()
    return [rows_by_doc_id[item.doc_id] for item in judge_inputs if item.doc_id in rows_by_doc_id], failures


def summarize_judge_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize rubric distributions with count/rate metrics."""
    per_label: dict[str, dict[str, Any]] = {}
    total_docs = len(rows)

    for label in PICO_LABELS:
        label_metrics: dict[str, Any] = {}
        for dimension, allowed_values in DIMENSION_VALUES.items():
            counter = Counter(
                row["labels"][label][dimension]
                for row in rows
                if isinstance(row.get("labels"), dict)
                and isinstance(row["labels"].get(label), dict)
                and isinstance(row["labels"][label].get(dimension), str)
            )
            label_metrics[dimension] = _distribution(counter, allowed_values, total_docs)
        per_label[label] = label_metrics

    overall: dict[str, Any] = {}
    for dimension, allowed_values in DIMENSION_VALUES.items():
        counter = Counter(
            row["overall"][dimension]
            for row in rows
            if isinstance(row.get("overall"), dict)
            and isinstance(row["overall"].get(dimension), str)
        )
        overall[dimension] = _distribution(counter, allowed_values, total_docs)

    return {
        "judge_evaluator_version": JUDGE_EVALUATOR_VERSION,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "counts": {
            "documents": total_docs,
        },
        "per_label": per_label,
        "overall": overall,
    }


def parse_judge_response_text(output_text: str) -> dict[str, Any]:
    """Parse and validate structured judge JSON response."""
    candidate_text = _extract_json_object_text(output_text)
    try:
        parsed = json.loads(candidate_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Judge response was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Judge response must be a JSON object")
    parsed = _normalize_common_payload_shapes(parsed)
    return _normalize_and_validate_judge_payload(parsed)


def _aggregate_predictions(raw_rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, list[str]]], dict[str, Any]]:
    by_doc: dict[str, dict[str, list[str]]] = {}
    invalid_rows = 0
    invalid_items = 0
    response_items = 0
    unknown_label_items = 0

    for row in raw_rows:
        doc_id = row.get("doc_id")
        response = row.get("response")
        if not isinstance(doc_id, str) or not isinstance(response, str):
            invalid_rows += 1
            continue
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            invalid_rows += 1
            continue

        items: list[Any]
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict) and isinstance(parsed.get("spans"), list):
            items = parsed["spans"]
        else:
            invalid_rows += 1
            continue

        target = by_doc.setdefault(doc_id, {label: [] for label in PICO_LABELS})
        for item in items:
            response_items += 1
            if not isinstance(item, dict):
                invalid_items += 1
                continue
            label = item.get("label")
            text = item.get("text")
            if not isinstance(label, str) or not isinstance(text, str):
                invalid_items += 1
                continue
            if label not in PICO_LABELS:
                invalid_items += 1
                unknown_label_items += 1
                continue
            target[label].append(text)

    return by_doc, {
        "raw_rows": len(raw_rows),
        "invalid_rows": invalid_rows,
        "response_items": response_items,
        "invalid_items": invalid_items,
        "unknown_label_items": unknown_label_items,
    }


def _judge_single_input(
    *,
    judge_input: JudgeInput,
    provider: str,
    model_id: str,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
    api_mode: str,
    prompt_template: str,
    prompt_version: str,
    max_retries: int,
) -> dict[str, Any]:
    attempt = 0
    while True:
        try:
            return _judge_single_input_once(
                judge_input=judge_input,
                provider=provider,
                model_id=model_id,
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                api_mode=api_mode,
                prompt_template=prompt_template,
                prompt_version=prompt_version,
            )
        except Exception:
            if attempt >= max_retries:
                raise
            attempt += 1
            time.sleep(min(2**attempt, 5))


def _judge_single_input_once(
    *,
    judge_input: JudgeInput,
    provider: str,
    model_id: str,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
    api_mode: str,
    prompt_template: str,
    prompt_version: str,
) -> dict[str, Any]:
    try:
        from openai import BadRequestError, NotFoundError, OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is required for LLM judge evaluation") from exc

    user_prompt = prompt_template.format(
        doc_id=judge_input.doc_id,
        abstract=judge_input.abstract,
        gold_p=json.dumps(judge_input.gold["P"], ensure_ascii=False),
        gold_i=json.dumps(judge_input.gold["I"], ensure_ascii=False),
        gold_o=json.dumps(judge_input.gold["O"], ensure_ascii=False),
        pred_p=json.dumps(judge_input.predicted["P"], ensure_ascii=False),
        pred_i=json.dumps(judge_input.predicted["I"], ensure_ascii=False),
        pred_o=json.dumps(judge_input.predicted["O"], ensure_ascii=False),
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict EBM-NLP PICO judge. "
                "For I, always evaluate intervention together with comparator/control when present. "
                "Return only JSON that matches the provided schema."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
    request_mode = api_mode
    try:
        if request_mode == "responses":
            response = client.responses.create(
                model=model_id,
                input=messages,
                temperature=0,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "judge_rubric",
                        "schema": _response_schema(),
                        "strict": True,
                    }
                },
            )
            parsed = parse_judge_response_text(response.output_text)
            response_id = getattr(response, "id", None)
        else:
            parsed, response_id, request_mode = _call_chat_completions(
                client=client,
                messages=messages,
                model_id=model_id,
            )
    except NotFoundError:
        if request_mode != "responses":
            raise
        parsed, response_id, request_mode = _call_chat_completions(
            client=client,
            messages=messages,
            model_id=model_id,
        )
    except BadRequestError:
        if request_mode != "responses":
            raise
        parsed, response_id, request_mode = _call_chat_completions(
            client=client,
            messages=messages,
            model_id=model_id,
        )

    return {
        "doc_id": judge_input.doc_id,
        "labels": parsed["labels"],
        "overall": parsed["overall"],
        "metadata": {
            "judge_model": model_id,
            "judge_prompt_version": prompt_version,
            "api_mode": request_mode,
            "provider": provider,
            "base_url": base_url,
            "openai_response_id": response_id,
        },
    }


def _call_chat_completions(
    *,
    client: Any,
    messages: list[dict[str, str]],
    model_id: str,
) -> tuple[dict[str, Any], Any, str]:
    try:
        from openai import BadRequestError
    except ImportError as exc:
        raise RuntimeError("The openai package is required for LLM judge evaluation") from exc

    attempts: list[tuple[str, dict[str, Any] | None]] = [
        (
            "chat_completions_json_schema",
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "judge_rubric",
                    "schema": _response_schema(),
                    "strict": True,
                },
            },
        ),
        ("chat_completions_json_object", {"type": "json_object"}),
        ("chat_completions_plain", None),
    ]
    last_error: Exception | None = None
    for mode_name, response_format in attempts:
        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": 0,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        try:
            response = client.chat.completions.create(**kwargs)
        except BadRequestError as exc:
            last_error = exc
            if not _is_response_format_error(exc):
                raise
            continue
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError("Chat completions response did not contain string content")
        return parse_judge_response_text(content), getattr(response, "id", None), mode_name
    if last_error is not None:
        raise last_error
    raise RuntimeError("chat.completions fallback exhausted without a response")


def _is_response_format_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "response_format" in message
        or "json_schema" in message
        or "json_object" in message
        or "text.format" in message
        or "missing_required_parameter" in message
    )


def _extract_json_object_text(output_text: str) -> str:
    text = output_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text


def _normalize_common_payload_shapes(parsed: dict[str, Any]) -> dict[str, Any]:
    candidate = _coerce_judge_payload(parsed)
    if candidate is not None:
        return candidate

    current: dict[str, Any] = parsed
    for _ in range(6):
        for key in ("judge_rubric", "result", "response", "data", "output", "payload", "content"):
            nested = current.get(key)
            if isinstance(nested, dict):
                candidate = _coerce_judge_payload(nested)
                if candidate is not None:
                    return candidate
                current = nested
                break
        else:
            for value in current.values():
                if isinstance(value, dict):
                    candidate = _coerce_judge_payload(value)
                    if candidate is not None:
                        return candidate
            return current
    return current


def _coerce_judge_payload(candidate: dict[str, Any]) -> dict[str, Any] | None:
    labels = candidate.get("labels")
    overall = candidate.get("overall")
    if isinstance(labels, dict) and isinstance(overall, dict):
        return candidate

    if isinstance(labels, dict):
        nested_overall = labels.get("overall")
        if isinstance(nested_overall, dict):
            pio_like = all(isinstance(labels.get(label), dict) for label in PICO_LABELS)
            if pio_like:
                return {
                    "labels": {label: labels[label] for label in PICO_LABELS},
                    "overall": nested_overall,
                }

    pio_like = all(isinstance(candidate.get(label), dict) for label in PICO_LABELS)
    if pio_like and isinstance(overall, dict):
        return {
            "labels": {label: candidate[label] for label in PICO_LABELS},
            "overall": overall,
        }

    return None


def _response_schema() -> dict[str, Any]:
    rubric_properties: dict[str, Any] = {
        "completeness": {"type": "string", "enum": list(COMPLETENESS_VALUES)},
        "accuracy": {"type": "string", "enum": list(ACCURACY_VALUES)},
        "noise": {"type": "string", "enum": list(NOISE_VALUES)},
        "granularity": {"type": "string", "enum": list(GRANULARITY_VALUES)},
        "overall_verdict": {"type": "string", "enum": list(VERDICT_VALUES)},
        "reason": {"type": "string"},
    }
    rubric_required = ["completeness", "accuracy", "noise", "granularity", "overall_verdict", "reason"]
    rubric_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": rubric_properties,
        "required": rubric_required,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "labels": {
                "type": "object",
                "additionalProperties": False,
                "properties": {label: rubric_schema for label in PICO_LABELS},
                "required": list(PICO_LABELS),
            },
            "overall": rubric_schema,
        },
        "required": ["labels", "overall"],
    }


def _normalize_and_validate_judge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    labels = payload.get("labels")
    overall = payload.get("overall")
    if not isinstance(labels, dict) or not isinstance(overall, dict):
        raise ValueError("Judge response must include object fields: labels and overall")

    normalized_labels: dict[str, dict[str, str]] = {}
    for label in PICO_LABELS:
        rubric = labels.get(label)
        if not isinstance(rubric, dict):
            raise ValueError(f"Judge response labels.{label} must be an object")
        normalized_labels[label] = _validate_rubric(rubric, field_prefix=f"labels.{label}")

    normalized_overall = _validate_rubric(overall, field_prefix="overall")
    return {
        "labels": normalized_labels,
        "overall": normalized_overall,
    }


def _validate_rubric(rubric: dict[str, Any], field_prefix: str) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for dimension, allowed_values in DIMENSION_VALUES.items():
        raw_value = rubric.get(dimension)
        if not isinstance(raw_value, str):
            raise ValueError(f"Judge response field {field_prefix}.{dimension} must be a string")
        value = raw_value.strip()
        if value not in allowed_values:
            raise ValueError(
                f"Judge response field {field_prefix}.{dimension} must be one of {allowed_values}; got {value!r}"
            )
        normalized[dimension] = value

    reason = rubric.get("reason")
    if not isinstance(reason, str):
        raise ValueError(f"Judge response field {field_prefix}.reason must be a string")
    clean_reason = re.sub(r"\s+", " ", reason).strip()
    if not clean_reason:
        raise ValueError(f"Judge response field {field_prefix}.reason must be non-empty")
    normalized["reason"] = clean_reason
    return normalized


def _distribution(counter: Counter[str], allowed_values: tuple[str, ...], total: int) -> dict[str, Any]:
    return {
        value: {
            "count": counter.get(value, 0),
            "rate": _safe_divide(counter.get(value, 0), total),
        }
        for value in allowed_values
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _read_prompt_template(prompt_version: str) -> str:
    return read_prompt_template(prompt_version)


class _ProgressPrinter:
    def __init__(self, total: int, enabled: bool) -> None:
        self.total = total
        self.enabled = enabled and total > 0
        self.completed = 0
        self._lock = threading.Lock()
        if self.enabled:
            print(f"[evaluate_llm_judge] queued {self.total} requests", file=sys.stderr, flush=True)

    def done(self, doc_id: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.completed += 1
            print(
                f"[evaluate_llm_judge] completed {self.completed}/{self.total} doc_id={doc_id}",
                file=sys.stderr,
                flush=True,
            )

    def failed(self, doc_id: str, message: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.completed += 1
            print(
                f"[evaluate_llm_judge] failed {self.completed}/{self.total} doc_id={doc_id} error={message}",
                file=sys.stderr,
                flush=True,
            )

    def finish(self) -> None:
        if not self.enabled:
            return
        print(f"[evaluate_llm_judge] finished {self.completed}/{self.total}", file=sys.stderr, flush=True)
