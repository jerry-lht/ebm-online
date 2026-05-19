"""Versioned prompt builder for criterion-wise screening."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from screening.pipeline.criteria import build_csmed_criterion_specs
from screening.schemas import CriterionGroup, CriterionSpec
from screening.schemas import InputSetting, ScreeningExample

CRITERIA_MODE_RAW = "raw"
CRITERIA_MODE_FIXED_SPECS = "fixed_specs"
CRITERIA_MODE_HYBRID_SPECS_RAW = "hybrid_specs_raw"
CRITERIA_MODES = (
    CRITERIA_MODE_RAW,
    CRITERIA_MODE_FIXED_SPECS,
    CRITERIA_MODE_HYBRID_SPECS_RAW,
)

JSON_TEMPLATE = """{
  "criterion_judgments": {
    "inc_1": {
      "text": "Adults with chronic kidney disease",
      "judgment": "yes"
    },
    "inc_2": {
      "text": "Randomized trial",
      "judgment": "unclear"
    },
    "exc_1": {
      "text": "Protocol-only publication",
      "judgment": "no"
    }
  }
}"""


@dataclass(frozen=True)
class CriterionWisePromptSpec:
    version: str
    template_path: Path
    style: str
    json_template: str
    supported_settings: frozenset[InputSetting]
    criteria_mode: str

    @property
    def template(self) -> str:
        return load_prompt_template(self.template_path)


@dataclass(frozen=True)
class CriterionWisePromptContext:
    example_id: str
    prompt_version: str
    question: str
    input_setting: str
    raw_review_criteria: str
    criterion_block: str
    candidate_block: str
    json_template: str


PROMPT_TEMPLATE_ROOT = Path(__file__).resolve().parent / "criterion_wise"


@lru_cache(maxsize=None)
def load_prompt_template(path: Path) -> str:
    """Load one prompt template file from disk."""
    return path.read_text(encoding="utf-8")


def _default_prompt_specs() -> dict[str, CriterionWisePromptSpec]:
    shared = {
        "template_path": PROMPT_TEMPLATE_ROOT / "v3.txt",
        "style": "strict_json",
        "json_template": JSON_TEMPLATE,
        "supported_settings": frozenset(
            {InputSetting.full_text_only, InputSetting.abstract_plus_full_text}
        ),
        "criteria_mode": CRITERIA_MODE_RAW,
    }
    return {
        "v1": CriterionWisePromptSpec(version="v1", **shared),
        "v2": CriterionWisePromptSpec(version="v2", **shared),
        "v3": CriterionWisePromptSpec(version="v3", **shared),
        "fixed_v1": CriterionWisePromptSpec(
            version="fixed_v1",
            template_path=PROMPT_TEMPLATE_ROOT / "fixed_specs_v1.txt",
            style="strict_json_fixed_specs",
            json_template=JSON_TEMPLATE,
            supported_settings=shared["supported_settings"],
            criteria_mode=CRITERIA_MODE_FIXED_SPECS,
        ),
        "hybrid_v1": CriterionWisePromptSpec(
            version="hybrid_v1",
            template_path=PROMPT_TEMPLATE_ROOT / "hybrid_specs_raw_v1.txt",
            style="strict_json_hybrid_specs_raw",
            json_template=JSON_TEMPLATE,
            supported_settings=shared["supported_settings"],
            criteria_mode=CRITERIA_MODE_HYBRID_SPECS_RAW,
        ),
    }


CRITERION_WISE_PROMPT_SPECS = _default_prompt_specs()


def get_criterion_wise_prompt_spec(prompt_version: str) -> CriterionWisePromptSpec:
    """Resolve a versioned criterion-wise prompt specification."""
    try:
        return CRITERION_WISE_PROMPT_SPECS[prompt_version]
    except KeyError as exc:
        raise ValueError(f"unsupported criterion-wise prompt version: {prompt_version}") from exc


def _render_raw_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        lines: list[str] = []
        for key, nested in value.items():
            rendered = _render_raw_value(nested)
            if rendered:
                lines.append(f"{key}: {rendered}")
        return "\n".join(lines) if lines else None
    if isinstance(value, list):
        rendered_items = [_render_raw_value(item) for item in value]
        cleaned = [item for item in rendered_items if item]
        if not cleaned:
            return None
        return "\n".join(f"- {item}" for item in cleaned)
    text = json.dumps(value, ensure_ascii=False)
    return text.strip() or None


def _format_raw_review_criteria(example: ScreeningExample) -> tuple[str, str]:
    raw = example.criteria.raw if isinstance(example.criteria.raw, dict) else {}
    criteria_prose = _render_raw_value(raw.get("criteria"))
    criteria_text_prose = _render_raw_value(raw.get("criteria_text"))
    blocks: list[str] = []
    source = "question_fallback"
    if criteria_prose:
        blocks.append("Review criteria section:")
        blocks.append(criteria_prose)
        source = "criteria"
    if criteria_text_prose:
        blocks.append("Criteria text fallback:")
        blocks.append(criteria_text_prose)
        source = "criteria_plus_criteria_text" if criteria_prose else "criteria_text"
    if not blocks:
        question = (example.question or "").strip() or "No review question provided."
        blocks.append("No explicit review criteria were available. Use the review question as the fallback eligibility intent:")
        blocks.append(question)
    return "\n\n".join(blocks), source


def _format_criterion_specs(specs: list[CriterionSpec], source: str) -> str:
    inclusion = [item for item in specs if item.criterion_group == CriterionGroup.inclusion]
    exclusion = [item for item in specs if item.criterion_group == CriterionGroup.exclusion]
    lines = [f"Fixed review criteria source: {source}"]
    if inclusion:
        lines.append("Inclusion criteria:")
        for spec in inclusion:
            lines.append(f"- {spec.criterion_id}: {spec.criterion_text}")
    else:
        lines.append("Inclusion criteria:\n- None provided")
    if exclusion:
        lines.append("Exclusion criteria:")
        for spec in exclusion:
            lines.append(f"- {spec.criterion_id}: {spec.criterion_text}")
    else:
        lines.append("Exclusion criteria:\n- None provided")
    return "\n".join(lines)


def _format_fixed_criteria(example: ScreeningExample) -> tuple[str, str, list[str]]:
    specs, source = build_csmed_criterion_specs(example)
    criterion_ids = [spec.criterion_id for spec in specs]
    return _format_criterion_specs(specs, source), source, criterion_ids


def _format_sections(label: str, sections: list[object]) -> str:
    if not sections:
        return f"{label}:\n[No sections provided]"
    lines = [f"{label}:"]
    for index, section in enumerate(sections, start=1):
        title = getattr(section, "title", None) or f"Section {index}"
        text = getattr(section, "text", "").strip() or "[Empty section]"
        source = getattr(section, "source", None)
        prefix = f"[{source}] " if source else ""
        lines.append(f"{index}. {prefix}{title}")
        lines.append(text)
    return "\n".join(lines)


def _candidate_text_block(example: ScreeningExample, setting: InputSetting) -> tuple[str, str]:
    title = (example.title or "").strip()
    abstract = (example.abstract or "").strip()

    if setting == InputSetting.full_text_only:
        return (
            "full_text_sections",
            "\n\n".join(
                [
                    "Candidate study:",
                    f"Title: {title or '[Missing title]'}",
                    f"Abstract: {abstract or '[Missing abstract]'}",
                    _format_sections("Full text sections", example.full_text_sections),
                ]
            ),
        )

    if setting == InputSetting.abstract_plus_full_text:
        return (
            "title_abstract_full_text_sections",
            "\n\n".join(
                [
                    "Candidate study:",
                    f"Title: {title or '[Missing title]'}",
                    f"Abstract: {abstract or '[Missing abstract]'}",
                    _format_sections("Full text sections", example.full_text_sections),
                ]
            ),
        )

    raise ValueError(f"unsupported input setting for criterion-wise prompt: {setting.value}")


def build_criterion_wise_prompt_context(
    example: ScreeningExample,
    *,
    setting: InputSetting,
    prompt_version: str,
    criteria_mode: str | None = None,
) -> tuple[CriterionWisePromptContext, dict[str, str]]:
    """Build structured rendering context plus prompt metadata."""
    spec = get_criterion_wise_prompt_spec(prompt_version)
    resolved_criteria_mode = criteria_mode or spec.criteria_mode
    if resolved_criteria_mode not in CRITERIA_MODES:
        raise ValueError(f"unsupported criteria mode: {resolved_criteria_mode}")
    if resolved_criteria_mode != spec.criteria_mode:
        raise ValueError(
            f"prompt version {prompt_version} is registered for criteria mode "
            f"{spec.criteria_mode}, not {resolved_criteria_mode}"
        )
    if setting not in spec.supported_settings:
        supported = ", ".join(sorted(item.value for item in spec.supported_settings))
        raise ValueError(
            f"prompt version {prompt_version} does not support input setting {setting.value}; "
            f"supported settings: {supported}"
        )

    raw_review_criteria, criteria_source = _format_raw_review_criteria(example)
    criterion_block = ""
    fixed_criteria_source = ""
    expected_criterion_ids: list[str] = []
    if resolved_criteria_mode in {CRITERIA_MODE_FIXED_SPECS, CRITERIA_MODE_HYBRID_SPECS_RAW}:
        criterion_block, fixed_criteria_source, expected_criterion_ids = _format_fixed_criteria(
            example
        )
    text_source, candidate_block = _candidate_text_block(example, setting)
    context = CriterionWisePromptContext(
        example_id=example.example_id,
        prompt_version=prompt_version,
        question=(example.question or "").strip() or "[Missing question]",
        input_setting=setting.value,
        raw_review_criteria=raw_review_criteria,
        criterion_block=criterion_block,
        candidate_block=candidate_block,
        json_template=spec.json_template,
    )
    metadata = {
        "prompt_version": prompt_version,
        "input_setting": setting.value,
        "text_source": text_source,
        "criteria_source": criteria_source,
        "criteria_mode": resolved_criteria_mode,
    }
    if fixed_criteria_source:
        metadata["fixed_criteria_source"] = fixed_criteria_source
    if expected_criterion_ids:
        metadata["expected_criterion_ids"] = ",".join(expected_criterion_ids)
    return context, metadata


def render_criterion_wise_prompt(
    spec: CriterionWisePromptSpec, context: CriterionWisePromptContext
) -> str:
    """Render one versioned criterion-wise prompt."""
    return spec.template.format(
        prompt_version=context.prompt_version,
        example_id=context.example_id,
        question=context.question,
        input_setting=context.input_setting,
        raw_review_criteria=context.raw_review_criteria,
        criterion_block=context.criterion_block,
        candidate_block=context.candidate_block,
        json_template=context.json_template,
    )


def build_criterion_wise_prompt(
    example: ScreeningExample,
    *,
    setting: InputSetting,
    prompt_version: str,
    criteria_mode: str | None = None,
) -> tuple[str, dict[str, str]]:
    """Build one criterion-wise prompt and prompt metadata."""
    context, metadata = build_criterion_wise_prompt_context(
        example,
        setting=setting,
        prompt_version=prompt_version,
        criteria_mode=criteria_mode,
    )
    spec = get_criterion_wise_prompt_spec(prompt_version)
    return render_criterion_wise_prompt(spec, context), metadata
