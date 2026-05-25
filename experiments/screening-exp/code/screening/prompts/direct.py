"""Versioned prompt builder for the direct criteria-aware LLM baseline."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from screening.schemas import InputSetting, ScreeningExample

SUPPORTED_CRITERIA = (
    "population",
    "intervention",
    "comparator",
    "outcome",
    "study_design",
)

JSON_TEMPLATE = """{
  "decision": "include",
  "criterion_judgments": {
    "population": {"judgment": "yes", "reason": "...", "evidence_spans": ["..."]},
    "intervention": {"judgment": "unclear", "reason": "...", "evidence_spans": []},
    "comparator": {"judgment": "not_applicable", "reason": "...", "evidence_spans": []},
    "outcome": {"judgment": "yes", "reason": "...", "evidence_spans": ["..."]},
    "study_design": {"judgment": "yes", "reason": "...", "evidence_spans": ["..."]}
  },
  "failed_criterion": null,
  "main_reason": "...",
  "evidence_spans": ["..."]
}"""

ABSTRACT_ONLY_V3_JSON_TEMPLATE = """{
  "decision": "include",
  "main_reason": "..."
}"""


@dataclass(frozen=True)
class DirectPromptSpec:
    version: str
    template_path: Path
    style: str
    json_template: str
    supported_settings: frozenset[InputSetting]
    
    @property
    def template(self) -> str:
        return load_prompt_template(self.template_path)


@dataclass(frozen=True)
class DirectPromptContext:
    example_id: str
    prompt_version: str
    question: str
    population: str
    intervention: str
    comparator: str
    outcome: str
    study_design: str
    inclusion_criteria: str
    exclusion_criteria: str
    candidate_block: str
    json_template: str


PROMPT_TEMPLATE_ROOT = Path(__file__).resolve().parent / "direct"


@lru_cache(maxsize=None)
def load_prompt_template(path: Path) -> str:
    """Load one prompt template file from disk."""
    return path.read_text(encoding="utf-8")


def _default_direct_prompt_specs() -> dict[str, DirectPromptSpec]:
    return {
        "v0": DirectPromptSpec(
            version="v0",
            template_path=PROMPT_TEMPLATE_ROOT / "v0.txt",
            style="strict_json",
            json_template=JSON_TEMPLATE,
            supported_settings=frozenset(
                {
                    InputSetting.abstract_only,
                    InputSetting.full_text_only,
                    InputSetting.abstract_plus_full_text,
                }
            ),
        ),
        "v1": DirectPromptSpec(
            version="v1",
            template_path=PROMPT_TEMPLATE_ROOT / "v1.txt",
            style="strict_json",
            json_template=JSON_TEMPLATE,
            supported_settings=frozenset(
                {
                    InputSetting.abstract_only,
                    InputSetting.full_text_only,
                    InputSetting.abstract_plus_full_text,
                }
            ),
        ),
        "v2": DirectPromptSpec(
            version="v2",
            template_path=PROMPT_TEMPLATE_ROOT / "v2.txt",
            style="strict_json",
            json_template=JSON_TEMPLATE,
            supported_settings=frozenset(
                {
                    InputSetting.abstract_only,
                    InputSetting.full_text_only,
                    InputSetting.abstract_plus_full_text,
                }
            ),
        ),
        "v3": DirectPromptSpec(
            version="v3",
            template_path=PROMPT_TEMPLATE_ROOT / "v3.txt",
            style="strict_json",
            json_template=ABSTRACT_ONLY_V3_JSON_TEMPLATE,
            supported_settings=frozenset({InputSetting.abstract_only}),
        ),
    }


DIRECT_PROMPT_SPECS: dict[str, DirectPromptSpec] = _default_direct_prompt_specs()


def get_direct_prompt_spec(prompt_version: str) -> DirectPromptSpec:
    """Resolve a versioned direct-prompt specification."""
    try:
        return DIRECT_PROMPT_SPECS[prompt_version]
    except KeyError as exc:
        raise ValueError(f"unsupported direct prompt version: {prompt_version}") from exc


def _format_list(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    if not cleaned:
        return "- None provided"
    return "\n".join(f"- {item}" for item in cleaned)


def _format_sections(label: str, sections: list[object]) -> str:
    if not sections:
        return f"{label}:\n- None provided"

    lines = [f"{label}:"]
    for index, section in enumerate(sections, start=1):
        title = getattr(section, "title", None) or f"Section {index}"
        text = getattr(section, "text", "").strip()
        source = getattr(section, "source", None)
        prefix = f"[{source}] " if source else ""
        lines.append(f"{index}. {prefix}{title}")
        lines.append(text if text else "[Empty section]")
    return "\n".join(lines)


def _candidate_text_block(example: ScreeningExample, setting: InputSetting) -> tuple[str, str]:
    title = (example.title or "").strip()
    abstract = (example.abstract or "").strip()
    has_abstract = bool(title or abstract)
    has_full_text = bool(example.full_text_sections)
    has_evidence_profile = bool(example.evidence_profile)

    if setting == InputSetting.abstract_only:
        if not has_abstract:
            raise ValueError("abstract_only prompt requires title or abstract")
        return (
            "abstract",
            "\n".join(
                [
                    "Candidate study:",
                    f"Title: {title or '[Missing title]'}",
                    f"Abstract: {abstract or '[Missing abstract]'}",
                ]
            ),
        )

    if setting == InputSetting.full_text_only:
        if has_full_text:
            return ("full_text_sections", _format_sections("Full text sections", example.full_text_sections))
        if has_evidence_profile:
            return (
                "evidence_profile_fallback",
                _format_sections("Evidence profile sections", example.evidence_profile),
            )
        raise ValueError("full_text_only prompt requires full_text_sections or evidence_profile")

    if setting == InputSetting.abstract_plus_full_text:
        if not has_abstract:
            raise ValueError("abstract_plus_full_text prompt requires title or abstract")
        if has_full_text:
            full_text_block = _format_sections("Full text sections", example.full_text_sections)
            source = "full_text_sections"
        elif has_evidence_profile:
            full_text_block = _format_sections("Evidence profile sections", example.evidence_profile)
            source = "evidence_profile_fallback"
        else:
            raise ValueError(
                "abstract_plus_full_text prompt requires full_text_sections or evidence_profile"
            )
        return (
            source,
            "\n\n".join(
                [
                    "Candidate study:",
                    f"Title: {title or '[Missing title]'}",
                    f"Abstract: {abstract or '[Missing abstract]'}",
                    full_text_block,
                ]
            ),
        )

    raise ValueError(f"unsupported input setting for direct prompt: {setting}")


def build_direct_prompt_context(
    example: ScreeningExample,
    *,
    setting: InputSetting,
    prompt_version: str,
) -> tuple[DirectPromptContext, dict[str, str]]:
    """Build structured rendering context plus prompt metadata."""
    spec = get_direct_prompt_spec(prompt_version)
    if setting not in spec.supported_settings:
        supported = ", ".join(sorted(item.value for item in spec.supported_settings))
        raise ValueError(
            f"prompt version {prompt_version} does not support input setting {setting.value}; "
            f"supported settings: {supported}"
        )
    text_source, candidate_block = _candidate_text_block(example, setting)
    pico = example.pico
    context = DirectPromptContext(
        example_id=example.example_id,
        prompt_version=prompt_version,
        question=example.question or "[Missing question]",
        population=pico.population or "[Not provided]",
        intervention=pico.intervention or "[Not provided]",
        comparator=str(pico.comparator) if pico.comparator is not None else "[Not provided]",
        outcome=pico.outcome or "[Not provided]",
        study_design=pico.study_design or "[Not provided]",
        inclusion_criteria=_format_list(example.criteria.inclusion),
        exclusion_criteria=_format_list(example.criteria.exclusion),
        candidate_block=candidate_block,
        json_template=spec.json_template,
    )
    metadata = {
        "prompt_version": prompt_version,
        "input_setting": setting.value,
        "text_source": text_source,
    }
    if spec.json_template == JSON_TEMPLATE:
        metadata["criteria_keys"] = ",".join(SUPPORTED_CRITERIA)
    return context, metadata


def render_direct_prompt(spec: DirectPromptSpec, context: DirectPromptContext) -> str:
    """Render a direct prompt from a versioned spec and structured context."""
    return spec.template.format(
        example_id=context.example_id,
        prompt_version=context.prompt_version,
        question=context.question,
        population=context.population,
        intervention=context.intervention,
        comparator=context.comparator,
        outcome=context.outcome,
        study_design=context.study_design,
        inclusion_criteria=context.inclusion_criteria,
        exclusion_criteria=context.exclusion_criteria,
        candidate_block=context.candidate_block,
        json_template=context.json_template,
    )


def build_direct_prompt(
    example: ScreeningExample,
    *,
    setting: InputSetting,
    prompt_version: str,
) -> tuple[str, dict[str, str]]:
    """Build the direct-baseline prompt and prompt metadata."""
    spec = get_direct_prompt_spec(prompt_version)
    context, metadata = build_direct_prompt_context(
        example,
        setting=setting,
        prompt_version=prompt_version,
    )
    return render_direct_prompt(spec, context), metadata
