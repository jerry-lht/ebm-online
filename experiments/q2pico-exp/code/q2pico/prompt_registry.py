from __future__ import annotations

from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def resolve_prompt_path(prompt_version: str) -> Path:
    matches = sorted(PROMPTS_DIR.rglob(f"{prompt_version}.txt"))
    if not matches:
        raise FileNotFoundError(f"Prompt template not found for version {prompt_version!r} under {PROMPTS_DIR}")
    if len(matches) > 1:
        raise RuntimeError(f"Multiple prompt templates found for version {prompt_version!r}: {matches}")
    return matches[0]


def read_prompt_template(prompt_version: str) -> str:
    return resolve_prompt_path(prompt_version).read_text(encoding="utf-8")
