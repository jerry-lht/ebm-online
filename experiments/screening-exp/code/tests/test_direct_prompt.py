from __future__ import annotations

import pytest

from screening.prompts.direct import (
    build_direct_prompt,
    build_direct_prompt_context,
    get_direct_prompt_spec,
    load_prompt_template,
    render_direct_prompt,
)
from screening.schemas import InputSetting, ScreeningExample, TextSection


def _example(setting: InputSetting) -> ScreeningExample:
    return ScreeningExample(
        example_id=f"example-{setting.value}",
        benchmark="csmed_ft",
        split="test-small",
        review_id="review-1",
        study_id="study-1",
        question="Should this study be included?",
        title="Trial title",
        abstract="Trial abstract",
        full_text_sections=[TextSection(title="Methods", text="Methods section text.")],
        criteria={
            "inclusion": ["Adults with CKD", "Randomized trials"],
            "exclusion": ["Protocol only"],
        },
        input_setting=setting,
    )


def test_build_direct_prompt_for_abstract_only() -> None:
    prompt, metadata = build_direct_prompt(
        _example(InputSetting.abstract_only),
        setting=InputSetting.abstract_only,
        prompt_version="v0",
    )

    assert "Title: Trial title" in prompt
    assert "Abstract: Trial abstract" in prompt
    assert "Full text sections" not in prompt
    assert "Do not output any prose before or after the JSON object." in prompt
    assert '"decision": "include"' in prompt
    assert '"confidence"' not in prompt
    assert "Use only the review information that is actually provided below" in prompt
    assert "Inclusion criteria:" not in prompt
    assert "PICO/PICOS:" not in prompt
    assert metadata["text_source"] == "abstract"
    assert metadata["prompt_version"] == "v0"


def test_direct_prompt_supports_versioned_spec_rendering() -> None:
    example = _example(InputSetting.abstract_only)
    context, metadata = build_direct_prompt_context(
        example,
        setting=InputSetting.abstract_only,
        prompt_version="v1",
    )
    spec = get_direct_prompt_spec("v1")
    prompt = render_direct_prompt(spec, context)

    assert "Task:" in prompt
    assert "Output contract:" in prompt
    assert "Question: Should this study be included?" in prompt
    assert "Some benchmark examples provide only the review question plus candidate title/abstract" in prompt
    assert metadata["prompt_version"] == "v1"
    assert spec.template_path.name == "v1.txt"


def test_direct_prompt_v2_uses_conservative_exclusion_policy() -> None:
    example = _example(InputSetting.abstract_only)
    context, metadata = build_direct_prompt_context(
        example,
        setting=InputSetting.abstract_only,
        prompt_version="v2",
    )
    spec = get_direct_prompt_spec("v2")
    prompt = render_direct_prompt(spec, context)

    assert "Use exclude only when the abstract provides clear evidence that the study is outside the review topic" in prompt
    assert "Term mismatch alone is not enough for exclusion" in prompt
    assert "If you cannot safely justify exclusion from the provided text, choose include" in prompt
    assert metadata["prompt_version"] == "v2"
    assert spec.template_path.name == "v2.txt"


def test_direct_prompt_v3_uses_minimal_abstract_only_contract() -> None:
    example = _example(InputSetting.abstract_only)
    context, metadata = build_direct_prompt_context(
        example,
        setting=InputSetting.abstract_only,
        prompt_version="v3",
    )
    spec = get_direct_prompt_spec("v3")
    prompt = render_direct_prompt(spec, context)

    assert "systematic review" in prompt
    assert "title/abstract screening" in prompt
    assert "potentially eligible" in prompt
    assert "Choose `exclude` only if the title or abstract clearly indicates the study is not eligible" in prompt
    assert "Otherwise choose `include`" in prompt
    assert "criterion_judgments" not in prompt
    assert "failed_criterion" not in prompt
    assert "evidence_spans" not in prompt
    assert "PICO" not in prompt
    assert "full text" not in prompt.lower()
    assert "Example ID:" not in prompt
    assert '"main_reason": "..."' in prompt
    assert "criteria_keys" not in metadata
    assert metadata["prompt_version"] == "v3"
    assert spec.template_path.name == "v3.txt"


def test_direct_prompt_loads_template_from_disk() -> None:
    spec = get_direct_prompt_spec("v0")
    template = load_prompt_template(spec.template_path)

    assert "Return exactly one JSON object." in template
    assert "{json_template}" in template


def test_direct_prompt_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="unsupported direct prompt version"):
        get_direct_prompt_spec("v999")


def test_build_direct_prompt_for_full_text_only() -> None:
    example = _example(InputSetting.full_text_only)
    prompt, metadata = build_direct_prompt(
        example,
        setting=InputSetting.full_text_only,
        prompt_version="v0",
    )

    assert "Full text sections" in prompt
    assert "Abstract: Trial abstract" not in prompt
    assert metadata["text_source"] == "full_text_sections"


def test_build_direct_prompt_rejects_v3_for_full_text_only() -> None:
    example = _example(InputSetting.full_text_only)

    with pytest.raises(
        ValueError,
        match="prompt version v3 does not support input setting full_text_only",
    ):
        build_direct_prompt(
            example,
            setting=InputSetting.full_text_only,
            prompt_version="v3",
        )


def test_build_direct_prompt_falls_back_to_evidence_profile() -> None:
    example = ScreeningExample(
        example_id="example-fallback",
        benchmark="q2crbench",
        split="test",
        review_id="review-1",
        study_id="study-1",
        title="Study title",
        abstract="Study abstract",
        evidence_profile=[TextSection(title="GRADE", text="Evidence profile text.")],
        input_setting=InputSetting.abstract_plus_full_text,
    )

    prompt, metadata = build_direct_prompt(
        example,
        setting=InputSetting.abstract_plus_full_text,
        prompt_version="v0",
    )

    assert "Evidence profile sections" in prompt
    assert metadata["text_source"] == "evidence_profile_fallback"


def test_build_direct_prompt_rejects_missing_required_text() -> None:
    example = ScreeningExample(
        example_id="example-missing",
        benchmark="csmed_ft",
        split="test",
        review_id="review-1",
        study_id="study-1",
        input_setting=InputSetting.full_text_only,
        full_text_sections=[TextSection(title="Methods", text="Methods.")],
    )

    with pytest.raises(ValueError, match="abstract_plus_full_text prompt requires title or abstract"):
        build_direct_prompt(
            example,
            setting=InputSetting.abstract_plus_full_text,
            prompt_version="v0",
        )
