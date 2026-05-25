"""JSON, JSONL, and prediction parsing helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from screening.schemas import (
    AbstractScreeningPrediction,
    BaseScreeningPrediction,
    InputSetting,
    RawResponseMetadata,
    ScreeningPrediction,
)

ModelT = TypeVar("ModelT", bound=BaseModel)
PredictionT = TypeVar("PredictionT", bound=BaseScreeningPrediction)

_JSON_FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def read_json(path: str | Path) -> Any:
    """Read a UTF-8 JSON document."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, data: Any) -> None:
    """Write a UTF-8 JSON document with stable formatting."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def read_jsonl(path: str | Path) -> list[Any]:
    """Read a JSONL file, skipping blank lines."""
    records: list[Any] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}: {exc.msg}") from exc
    return records


def write_jsonl(path: str | Path, records: Iterable[Any]) -> None:
    """Write records to JSONL with one compact JSON object per line."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            if isinstance(record, BaseModel):
                payload = record.model_dump(mode="json")
            else:
                payload = record
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def read_model_jsonl(path: str | Path, model_type: type[ModelT]) -> list[ModelT]:
    """Read a JSONL file and validate every record as a Pydantic model."""
    return [model_type.model_validate(record) for record in read_jsonl(path)]


def write_model_jsonl(path: str | Path, records: Iterable[BaseModel]) -> None:
    """Write Pydantic models to JSONL."""
    write_jsonl(path, records)


def append_jsonl(path: str | Path, records: Iterable[Any]) -> None:
    """Append records to a JSONL file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for record in records:
            if isinstance(record, BaseModel):
                payload = record.model_dump(mode="json")
            else:
                payload = record
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _sanitize_raw_json_candidate(raw_response: str) -> str:
    candidate = raw_response.strip()
    fenced = _JSON_FENCE_PATTERN.match(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    return candidate


def parse_json_response(raw_response: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse a raw LLM response expected to contain one JSON object."""
    sanitized = _sanitize_raw_json_candidate(raw_response)
    try:
        parsed = json.loads(sanitized)
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON response: {exc.msg}"]

    if not isinstance(parsed, dict):
        return None, ["JSON response must be an object"]
    return parsed, []


def format_validation_errors(exc: ValidationError) -> list[str]:
    """Convert Pydantic validation errors into compact path-prefixed messages."""
    messages: list[str] = []
    for error in exc.errors():
        loc = ".".join(str(item) for item in error.get("loc", ()))
        message = error.get("msg", "validation error")
        messages.append(f"{loc}: {message}" if loc else message)
    return messages


def validate_prediction(
    data: dict[str, Any],
    *,
    prediction_model: type[PredictionT] = ScreeningPrediction,
) -> tuple[PredictionT | None, list[str]]:
    """Validate and normalize a prediction dictionary."""
    try:
        return prediction_model.model_validate(data), []
    except ValidationError as exc:
        return None, format_validation_errors(exc)


def _prediction_model_for_setting(
    *,
    input_setting: InputSetting | None,
    prediction_schema: str | None,
    record: dict[str, Any] | None = None,
) -> type[BaseScreeningPrediction]:
    if prediction_schema == "abstract_only_v3" or (
        prediction_schema is None and input_setting == InputSetting.abstract_only
    ):
        if record is not None and any(
            key in record for key in ("criterion_judgments", "failed_criterion", "evidence_spans")
        ):
            return ScreeningPrediction
        return AbstractScreeningPrediction
    return ScreeningPrediction


def read_prediction_jsonl(path: str | Path) -> list[BaseScreeningPrediction]:
    """Read prediction records from JSONL and validate the recorded schema variant."""
    records: list[BaseScreeningPrediction] = []
    for raw_record in read_jsonl(path):
        if not isinstance(raw_record, dict):
            raise ValueError("prediction records must be JSON objects")
        metadata = raw_record.get("metadata")
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        prediction_schema = metadata_dict.get("prediction_schema")
        input_setting = None
        if isinstance(metadata_dict.get("input_setting"), str):
            try:
                input_setting = InputSetting(metadata_dict["input_setting"])
            except ValueError:
                input_setting = None
        model_type = _prediction_model_for_setting(
            input_setting=input_setting,
            prediction_schema=prediction_schema if isinstance(prediction_schema, str) else None,
            record=raw_record,
        )
        prediction, errors = validate_prediction(raw_record, prediction_model=model_type)
        if prediction is None:
            raise ValueError("; ".join(errors))
        records.append(prediction)
    return records


def normalize_prediction_response(
    *,
    example_id: str,
    raw_response: str,
    provider: str | None = None,
    model: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    prediction_model: type[PredictionT] = ScreeningPrediction,
) -> tuple[PredictionT | None, RawResponseMetadata]:
    """Parse a raw response and return either a prediction or auditable errors."""
    parsed, parse_errors = parse_json_response(raw_response)
    response_metadata = RawResponseMetadata(
        raw_response=raw_response,
        parsed_json=parsed,
        validation_errors=parse_errors.copy(),
        provider=provider,
        model=model,
        request_id=request_id,
        metadata=metadata or {},
    )
    if parsed is None:
        return None, response_metadata

    prediction_data = {"example_id": example_id, **parsed}
    prediction, validation_errors = validate_prediction(
        prediction_data,
        prediction_model=prediction_model,
    )
    response_metadata.validation_errors.extend(validation_errors)
    if prediction is None:
        return None, response_metadata

    prediction.raw_response_metadata = response_metadata
    return prediction, response_metadata
