"""Load shared LLM prompt templates and JSON schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_LLM_ROOT = Path(__file__).resolve().parents[3] / "shared" / "llm"


def load_prompt(name: str) -> str:
    path = _LLM_ROOT / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def load_schema(name: str) -> dict[str, Any]:
    path = _LLM_ROOT / "schemas" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))
