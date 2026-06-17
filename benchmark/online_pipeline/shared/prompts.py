"""Prompt template helpers for benchmark evaluators."""

from __future__ import annotations

from pathlib import Path


def render_prompt_template(path: str | Path, values: dict[str, str]) -> str:
    template = Path(path).read_text(encoding="utf-8")
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered
