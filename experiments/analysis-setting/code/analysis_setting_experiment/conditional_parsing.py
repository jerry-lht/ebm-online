from __future__ import annotations

import json
from typing import Any

from .conditional_normalization import clean_text
from .conditional_specs import get_conditional_task_spec


def _extract_json_object(raw_output: str) -> str:
    text = raw_output.strip()
    if not text:
        raise ValueError("empty_raw_output")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("json_object_not_found")
    return text[start : end + 1]


def _validate_arm_pairs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("arm_pairs_not_array")
    validated: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("arm_pair_not_object")
        experimental = item.get("experimental_arm")
        control = item.get("control_arm")
        if not isinstance(experimental, str) or not isinstance(control, str):
            raise ValueError("arm_pair_non_string")
        validated.append({"experimental_arm": experimental, "control_arm": control})
    return validated


def _validate_structured_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("items_not_array")
    validated: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("item_not_object")
        comparison = item.get("comparison")
        if not isinstance(comparison, str):
            raise ValueError("comparison_non_string")
        validated.append(
            {
                "comparison": comparison,
                "arm_pairs": _validate_arm_pairs(item.get("arm_pairs")),
            }
        )
    return validated


def validate_conditional_prediction(task_name: str, parsed: Any) -> dict[str, Any]:
    spec = get_conditional_task_spec(task_name)
    if not isinstance(parsed, dict):
        raise ValueError("root_not_object")
    keys = set(parsed)
    expected_key = spec.target_key
    if expected_key not in keys:
        raise ValueError(f"missing_key:{expected_key}")
    if task_name in {"data_type", "candidate_effect_measure"}:
        value = parsed[expected_key]
        if not isinstance(value, str):
            raise ValueError(f"non_string_field:{expected_key}")
        return {expected_key: clean_text(value)}
    if task_name == "comparisons":
        value = parsed[expected_key]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError("comparisons_not_string_array")
        return {"comparisons": list(value)}
    if task_name == "arm_pairs":
        return {"arm_pairs": _validate_arm_pairs(parsed[expected_key])}
    if task_name == "comparisons_and_arm_pairs":
        return {"items": _validate_structured_items(parsed[expected_key])}
    raise ValueError(f"unknown_conditional_task:{task_name}")


def parse_conditional_prediction(task_name: str, raw_output: str) -> dict[str, Any]:
    try:
        blob = _extract_json_object(raw_output)
        parsed = json.loads(blob)
        validated = validate_conditional_prediction(task_name, parsed)
        return {
            "parse_status": "success",
            "schema_valid": True,
            "parsed_prediction_json": validated,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "parse_status": "invalid_output",
            "schema_valid": False,
            "parsed_prediction_json": {},
            "error": str(exc),
        }

