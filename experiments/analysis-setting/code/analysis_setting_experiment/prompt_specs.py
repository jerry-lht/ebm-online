from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


_PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"


@dataclass(frozen=True)
class PromptSpec:
    version: str
    prompt_template_path: Path
    few_shots_path: Path | None = None


def _build_prompt_spec(version_dir: Path) -> PromptSpec | None:
    prompt_template_path = version_dir / "prompt.txt"
    if not prompt_template_path.exists():
        return None
    few_shots_path = version_dir / "few_shots.txt"
    return PromptSpec(
        version=version_dir.name,
        prompt_template_path=prompt_template_path,
        few_shots_path=few_shots_path if few_shots_path.exists() else None,
    )


def discover_prompt_specs(prompts_root: Path | None = None) -> dict[str, PromptSpec]:
    root = prompts_root or _PROMPTS_ROOT
    specs: dict[str, PromptSpec] = {}
    if not root.exists():
        return specs
    for version_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        spec = _build_prompt_spec(version_dir)
        if spec is None:
            continue
        specs[spec.version] = spec
    return specs


PROMPT_SPECS = discover_prompt_specs()


def get_prompt_spec(version: str) -> PromptSpec:
    try:
        return PROMPT_SPECS[version]
    except KeyError as exc:
        raise ValueError(f"unknown_prompt_version:{version}") from exc
