from __future__ import annotations

import json
from typing import Any

from .constants import LIST_FIELDS, REQUIRED_FIELDS, STRING_FIELDS


def _extract_json_array(raw_output: str) -> str:
    text = raw_output.strip()
    if not text:
        raise ValueError("empty_raw_output")
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("json_array_not_found")
    return text[start : end + 1]


def validate_candidate(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise ValueError("candidate_not_object")
    missing = [field for field in REQUIRED_FIELDS if field not in candidate]
    if missing:
        raise ValueError(f"missing_fields:{','.join(missing)}")
    extra = {key for key in candidate if key not in REQUIRED_FIELDS}
    if extra:
        candidate = {key: candidate[key] for key in REQUIRED_FIELDS}
    validated: dict[str, Any] = {}
    for field in STRING_FIELDS:
        value = candidate[field]
        if value is None:
            raise ValueError(f"null_field:{field}")
        if not isinstance(value, str):
            raise ValueError(f"non_string_field:{field}")
        validated[field] = value
    for field in LIST_FIELDS:
        value = candidate[field]
        if value is None:
            raise ValueError(f"null_field:{field}")
        if not isinstance(value, list):
            raise ValueError(f"non_list_field:{field}")
        if field == "arm_pairs":
            arm_pairs: list[dict[str, str]] = []
            for item in value:
                if not isinstance(item, dict):
                    raise ValueError("arm_pair_not_object")
                experimental = item.get("experimental_arm")
                control = item.get("control_arm")
                if experimental is None or control is None:
                    raise ValueError("arm_pair_missing_field")
                if not isinstance(experimental, str) or not isinstance(control, str):
                    raise ValueError("arm_pair_non_string")
                arm_pairs.append(
                    {
                        "experimental_arm": experimental,
                        "control_arm": control,
                    }
                )
            validated[field] = arm_pairs
        else:
            if any(not isinstance(item, str) for item in value):
                raise ValueError(f"list_item_non_string:{field}")
            validated[field] = list(value)
    return validated


def parse_prediction(raw_output: str) -> dict[str, Any]:
    try:
        json_blob = _extract_json_array(raw_output)
        parsed = json.loads(json_blob)
        if not isinstance(parsed, list):
            raise ValueError("root_not_array")
        validated = [validate_candidate(item) for item in parsed]
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
            "parsed_prediction_json": [],
            "error": str(exc),
        }

