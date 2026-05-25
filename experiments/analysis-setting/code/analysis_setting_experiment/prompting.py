from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .constants import PROMPT_VERSION, REQUIRED_FIELDS
from .prompt_specs import PromptSpec, get_prompt_spec

_LIST_SCHEMA_FIELDS = {"comparisons", "arm_pairs", "subgroup_candidates", "timepoints", "reported_outcome_measures"}


@lru_cache(maxsize=None)
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_schema_text() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {
            field: "string" if field not in _LIST_SCHEMA_FIELDS else "array"
            for field in REQUIRED_FIELDS
        },
    }


def _build_payload(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_title": review.get("sr_title", ""),
        "sr_pico": review.get("sr_pico", {}),
        "studies": review.get("studies", []),
    }


def _build_template_context(review: dict[str, Any], spec: PromptSpec) -> dict[str, str]:
    payload = _build_payload(review)
    schema_text = _build_schema_text()
    few_shots_section = ""
    if spec.few_shots_path is not None:
        few_shots_section = _read_text(spec.few_shots_path)
    return {
        "prompt_version": spec.version,
        "required_schema_keys": ", ".join(REQUIRED_FIELDS),
        "input_payload_json": json.dumps(payload, ensure_ascii=False, indent=2),
        "output_schema_json": json.dumps(schema_text, ensure_ascii=False, indent=2),
        "few_shots_section": few_shots_section,
    }


def build_prompt(review: dict[str, Any], *, prompt_version: str | None = None) -> str:
    spec = get_prompt_spec(prompt_version or PROMPT_VERSION)
    template = _read_text(spec.prompt_template_path)
    return template.format(**_build_template_context(review, spec))
