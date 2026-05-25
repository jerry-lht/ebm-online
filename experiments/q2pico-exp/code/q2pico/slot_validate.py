"""Validation for raw Question-to-PICO slot predictions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from q2pico.schemas import OUTPUT_KEY_TO_LABEL, PICO_LABELS, QuestionPICOExample, SlotPrediction, coerce_slot_dict

LLM_VALIDATOR_VERSION = "question-slot-validator-v1"


@dataclass
class _Counts:
    raw_rows: int = 0
    response_items: int = 0
    invalid_json_rows: int = 0
    schema_invalid_rows: int = 0
    non_list_slot_rows: int = 0
    non_string_items: int = 0
    duplicate_values: int = 0
    empty_values: int = 0
    written_values: int = 0
    unknown_question_rows: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


def validate_slot_predictions(
    examples: list[QuestionPICOExample],
    raw_rows: list[dict[str, Any]],
    *,
    labels: tuple[str, ...] = PICO_LABELS,
) -> tuple[list[SlotPrediction], dict[str, Any]]:
    example_ids = {example.question_id for example in examples}
    counts = _Counts()
    predictions_by_id: dict[str, SlotPrediction] = {}

    for row_index, row in enumerate(raw_rows, start=1):
        counts.raw_rows += 1
        question_id = row.get("question_id")
        response = row.get("response")
        if not isinstance(question_id, str) or not isinstance(response, str):
            counts.schema_invalid_rows += 1
            _record_error(counts, row_index, "row_schema_invalid", "raw row requires string question_id and response")
            continue
        if question_id not in example_ids:
            counts.unknown_question_rows += 1
            counts.schema_invalid_rows += 1
            _record_error(counts, row_index, "unknown_question_id", f"unknown question_id: {question_id!r}")
            continue
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            counts.invalid_json_rows += 1
            _record_error(counts, row_index, "invalid_json", "response is not valid JSON")
            continue
        if not isinstance(parsed, dict):
            counts.schema_invalid_rows += 1
            _record_error(counts, row_index, "payload_not_object", "response JSON must be an object")
            continue
        try:
            normalized_slots, row_counts = _normalize_payload(parsed, labels=labels)
        except _SchemaValidationError as exc:
            counts.schema_invalid_rows += 1
            counts.non_list_slot_rows += int(exc.error_type == "non_list_slot")
            counts.non_string_items += int(exc.error_type == "non_string_item")
            _record_error(counts, row_index, exc.error_type, exc.message)
            continue

        counts.response_items += row_counts["response_items"]
        counts.duplicate_values += row_counts["duplicate_values"]
        counts.empty_values += row_counts["empty_values"]
        counts.written_values += sum(len(values) for values in normalized_slots.values())
        full_slots = {label: [] for label in PICO_LABELS}
        full_slots.update(normalized_slots)
        predictions_by_id[question_id] = SlotPrediction(
            question_id=question_id,
            slots=full_slots,
            metadata={
                "validator_version": LLM_VALIDATOR_VERSION,
                "source_row_index": row_index,
                "labels": list(labels),
            },
        )

    ordered_predictions = [
        predictions_by_id[example.question_id]
        for example in examples
        if example.question_id in predictions_by_id
    ]
    quality = _build_quality(counts)
    return ordered_predictions, quality


class _SchemaValidationError(ValueError):
    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message


def _normalize_payload(
    payload: dict[str, Any],
    *,
    labels: tuple[str, ...],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    canonical_slots: dict[str, Any]
    keys = set(payload)
    allowed_output_keys = {label_key for label_key, label in OUTPUT_KEY_TO_LABEL.items() if label in labels}
    if keys <= set(labels):
        missing = set(labels) - keys
        if missing:
            raise _SchemaValidationError("missing_slot_keys", f"payload is missing canonical slots: {sorted(missing)}")
        canonical_slots = payload
    elif keys <= allowed_output_keys:
        if len(keys) != 1:
            raise _SchemaValidationError(
                "unknown_slot_keys",
                "single-label keyed payload must contain exactly one of participants/interventions/comparators/outcomes",
            )
        canonical_slots = {label: [] for label in labels}
        key = next(iter(keys))
        canonical_slots[OUTPUT_KEY_TO_LABEL[key]] = payload[key]
    else:
        raise _SchemaValidationError("unknown_slot_keys", f"payload has unsupported keys: {sorted(keys)}")

    response_items = 0
    duplicate_values = 0
    empty_values = 0
    normalized: dict[str, list[str]] = {}
    for label in labels:
        values = canonical_slots.get(label, [])
        if not isinstance(values, list):
            raise _SchemaValidationError("non_list_slot", f"slot {label} must be a list")
        clean_values: list[str] = []
        seen: set[str] = set()
        for item in values:
            response_items += 1
            if not isinstance(item, str):
                raise _SchemaValidationError("non_string_item", f"slot {label} contains a non-string item")
            stripped = item.strip()
            if not stripped:
                empty_values += 1
                continue
            if stripped in seen:
                duplicate_values += 1
                continue
            seen.add(stripped)
            clean_values.append(stripped)
        normalized[label] = clean_values
    return coerce_slot_dict(normalized, labels=labels), {
        "response_items": response_items,
        "duplicate_values": duplicate_values,
        "empty_values": empty_values,
    }


def _record_error(counts: _Counts, row_index: int, error_type: str, message: str) -> None:
    counts.errors.append(
        {
            "row_index": row_index,
            "error_type": error_type,
            "message": message,
        }
    )


def _build_quality(counts: _Counts) -> dict[str, Any]:
    denominator = counts.raw_rows or 1
    item_denominator = counts.response_items or 1
    return {
        "validator_version": LLM_VALIDATOR_VERSION,
        "counts": {
            "raw_rows": counts.raw_rows,
            "response_items": counts.response_items,
            "written_values": counts.written_values,
            "invalid_json_rows": counts.invalid_json_rows,
            "schema_invalid_rows": counts.schema_invalid_rows,
            "non_list_slot_rows": counts.non_list_slot_rows,
            "non_string_items": counts.non_string_items,
            "duplicate_values": counts.duplicate_values,
            "empty_values": counts.empty_values,
            "unknown_question_rows": counts.unknown_question_rows,
        },
        "invalid_json_rate": counts.invalid_json_rows / denominator,
        "schema_invalid_rate": counts.schema_invalid_rows / denominator,
        "non_list_slot_rate": counts.non_list_slot_rows / denominator,
        "non_string_item_rate": counts.non_string_items / item_denominator,
        "duplicate_value_rate": counts.duplicate_values / item_denominator,
        "empty_value_rate": counts.empty_values / item_denominator,
        "errors": counts.errors,
    }
