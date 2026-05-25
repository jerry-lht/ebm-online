from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .conditional_constants import CONDITIONAL_PROMPT_VERSION, MAX_FULL_TEXT_CHARS_PER_STUDY
from .conditional_experiment import (
    COMPARISONS_BENCHMARK_PROMPT_VERSION,
    COMPARISONS_REVIEW_LEVEL_PROMPT_VERSION,
    COMPARISONS_TASK,
    DEFAULT_DECISION_STRATEGY,
    DEFAULT_EVIDENCE_STRATEGY,
    EFFECT_MEASURE_TASK,
    load_few_shot_text,
)
from .conditional_comparison_candidates import build_comparison_candidates
from .conditional_normalization import clean_text, normalize_text
from .conditional_specs import (
    get_conditional_task_spec,
    get_effect_measure_selection_guidance,
    get_effect_measure_selection_options,
)
from .prompt_specs import get_prompt_spec

_FAMILY_AWARE_PROFILES = {
    "continuous": {
        "sections": ("methods", "results", "outcome measures", "statistical analysis"),
        "keywords": (
            "scale",
            "instrument",
            "questionnaire",
            "same scale",
            "different scales",
            "standardized",
            "change from baseline",
            "endpoint",
            "post-treatment score",
        ),
    },
    "dichotomous": {
        "sections": (),
        "keywords": (
            "risk ratio",
            "relative risk",
            "odds ratio",
            "adjusted odds",
            "logistic",
            "risk difference",
            "absolute risk",
            "peto",
            "rare events",
        ),
    },
    "contrast level": {
        "sections": (),
        "keywords": (
            "hazard ratio",
            "time to event",
            "survival",
            "incidence rate",
            "person-time",
            "rate ratio",
        ),
    },
}


@lru_cache(maxsize=None)
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _study_header(evidence_row: dict[str, Any]) -> str:
    return (
        f"Study ID: {clean_text(evidence_row.get('study_id'))}\n"
        f"Study Year: {clean_text(evidence_row.get('study_year'))}\n"
        f"Title: {clean_text(evidence_row.get('primary_report_title'))}\n"
        f"Evidence Tier: {clean_text(evidence_row.get('evidence_tier'))}"
    )


def _section_priority(section_name: str, preferred_sections: tuple[str, ...]) -> int:
    normalized = normalize_text(section_name)
    for index, hint in enumerate(preferred_sections):
        if normalize_text(hint) in normalized:
            return index
    return 999


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    normalized = normalize_text(text)
    return sum(1 for keyword in keywords if normalize_text(keyword) in normalized)


def _truncate_sections(sections: list[dict[str, str]], *, char_budget: int) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    used = 0
    for section in sections:
        name = clean_text(section.get("section")) or "Section"
        text = clean_text(section.get("text"))
        if not text:
            continue
        chunk = f"{name}\n{text}"
        if used >= char_budget:
            break
        remaining = char_budget - used
        if len(chunk) > remaining:
            text = text[: max(remaining - len(name) - 1, 0)].rstrip()
            if not text:
                continue
            chunk = f"{name}\n{text}"
        selected.append({"section": name, "text": text})
        used += len(chunk) + 2
    return selected


def _family_aware_sections(evidence_row: dict[str, Any], condition_data_type: str) -> list[dict[str, str]]:
    profile = _FAMILY_AWARE_PROFILES.get(normalize_text(condition_data_type), {"sections": (), "keywords": ()})
    sections = [
        {
            "section": clean_text(section.get("section")) or "Section",
            "text": clean_text(section.get("text")),
        }
        for section in evidence_row.get("full_text_sections", [])
        if clean_text(section.get("text"))
    ]
    if not sections:
        return []
    scored: list[tuple[int, int, int, int, dict[str, str]]] = []
    for index, section in enumerate(sections):
        priority = _section_priority(section["section"], profile["sections"])
        score = _keyword_score(f"{section['section']}\n{section['text']}", profile["keywords"])
        is_priority = 0 if (priority < 999 or score > 0) else 1
        scored.append((is_priority, priority, -score, index, section))
    scored.sort(key=lambda item: item[:4])
    prioritized = [item[4] for item in scored if item[0] == 0]
    selected = _truncate_sections(prioritized, char_budget=MAX_FULL_TEXT_CHARS_PER_STUDY)
    joined = "\n\n".join(f"{section['section']}\n{section['text']}" for section in selected)
    if len(joined) < min(1800, MAX_FULL_TEXT_CHARS_PER_STUDY):
        seen = {(section["section"], section["text"]) for section in selected}
        remainder = [section for section in sections if (section["section"], section["text"]) not in seen]
        selected = _truncate_sections(selected + remainder, char_budget=MAX_FULL_TEXT_CHARS_PER_STUDY)
    return selected


def _render_study_evidence(
    evidence_rows: list[dict[str, Any]],
    *,
    task_name: str,
    evidence_strategy: str,
    condition_data_type: str,
) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for row in evidence_rows:
        source = clean_text(row.get("evidence_source"))
        body = clean_text(row.get("text"))
        if (
            task_name == EFFECT_MEASURE_TASK
            and evidence_strategy == "family_aware_evidence"
            and source == "full_text"
            and row.get("full_text_sections")
        ):
            selected_sections = _family_aware_sections(row, condition_data_type)
            if selected_sections:
                body = f"{_study_header(row)}\n\n" + "\n\n".join(
                    f"{section['section']}\n{section['text']}" for section in selected_sections
                )
            elif clean_text(row.get("abstract_text")):
                body = f"{_study_header(row)}\n\n{clean_text(row.get('abstract_text'))}"
        elif source != "full_text" and clean_text(row.get("abstract_text")):
            body = f"{_study_header(row)}\n\n{clean_text(row.get('abstract_text'))}"
        rendered.append(
            {
                "study_id": clean_text(row.get("study_id")),
                "study_year": clean_text(row.get("study_year")),
                "primary_report_title": clean_text(row.get("primary_report_title")),
                "evidence_tier": clean_text(row.get("evidence_tier")),
                "evidence_source": source,
                "has_tables": bool(row.get("has_tables")),
                "text": body,
            }
        )
    return rendered


def _few_shots_section(prompt_version: str, few_shot_set: str | None) -> str:
    chunks: list[str] = []
    prompt_spec = get_prompt_spec(prompt_version)
    if prompt_spec.few_shots_path is not None:
        text = _read_text(prompt_spec.few_shots_path).strip()
        if text:
            chunks.append(text)
    explicit = load_few_shot_text(few_shot_set)
    if explicit:
        chunks.append(explicit)
    if not chunks:
        return ""
    return "Few-shot examples:\n" + "\n\n".join(chunks)


def _comparison_branch_instructions(task_name: str, prompt_version: str, decision_strategy: str) -> str:
    if task_name != COMPARISONS_TASK:
        return ""
    if decision_strategy == "constrained_selection":
        return (
            "\nAdditional comparisons constrained-selection rules:\n"
            "- You will receive a comparison candidate list. Return only comparisons copied exactly from that list.\n"
            "- Do not paraphrase, merge, split, or invent labels outside the candidate list.\n"
            "- Select a candidate only when the review-level evidence supports that comparison for this outcome.\n"
            "- Prefer grouped review-level family labels over study-level atomic pairs when the evidence is aggregated at the family level.\n"
            "- When uncertain, leave the candidate unselected. Returning an empty array is allowed."
        )
    if prompt_version == COMPARISONS_BENCHMARK_PROMPT_VERSION:
        return (
            "\nAdditional comparisons benchmark-aligned rules:\n"
            "- Recover the benchmark label set, not a generic intervention-versus-control paraphrase.\n"
            "- A benchmark comparison can be a simple review-level label such as choice, confidence, consultation length, or decisional conflict. Do not force every comparison into an X versus Y pair.\n"
            "- A benchmark comparison can also be a grouped family label such as psychological interventions vs inactive control, service system approaches vs inactive control, MBIs versus active comparators, or nHFV vs other non-invasive respiratory therapy modalities. Preserve that family label when that is how the review synthesizes the evidence.\n"
            "- If the benchmark uses atomic comparison labels with timepoint, subgroup, setting, or arm-detail modifiers, keep those modifiers when they are part of the review-level comparison label.\n"
            "- Do not replace benchmark labels with study-arm names, PICO categories, or broader umbrella labels unless the evidence clearly supports the benchmark label itself.\n"
            "- Use the review's own abstraction level. Some outputs are single labels, some are family labels, and some are detailed atomic labels.\n"
            "- Do not add subgroup, timepoint, or population modifiers unless they are part of the benchmark-style comparison label used by the review.\n"
            "- When evidence supports both a grouped family label and several study-level pairs, prefer whichever form best matches the benchmark-style review synthesis.\n"
            "Positive and negative examples:\n"
            "- Correct: choice. Incorrect: decision aid versus information provision when the benchmark label is the single review-level comparison choice.\n"
            "- Correct: psychological interventions vs inactive control. Incorrect: psychological interventions vs placebo; psychological interventions vs waiting list; psychological interventions vs usual care when the benchmark groups them together.\n"
            "- Correct: mbis versus active comparators. Incorrect: mindfulness versus usual care when the benchmark abstracts to a comparator family.\n"
            "- Correct: lower cad/cam nitinol vs rectangular chain retainers at 6 months. Incorrect: cad/cam retainer versus rectangular chain retainer if the benchmark keeps the side and timepoint detail.\n"
            "- Correct: [] when no supported benchmark-style comparison can be recovered. Incorrect: invent a comparison from outcome wording alone."
        )
    if prompt_version != COMPARISONS_REVIEW_LEVEL_PROMPT_VERSION:
        return ""
    return (
        "\nAdditional comparisons review-level rules:\n"
        "- Prefer the final review-level comparison label used by the review authors, not a study-by-study arm inventory.\n"
        "- If the review groups evidence under labels such as inactive control, active comparator, or another grouped comparator family, keep that grouped label and do not expand it into placebo, usual care, waiting list, or individual named controls.\n"
        "- Do not enumerate every study-level A vs B pair just to maximize evidence coverage.\n"
        "- When uncertain, under-report rather than over-generate unsupported atomic comparisons.\n"
        "Positive and negative examples:\n"
        "- Correct: psychological interventions versus inactive control. Incorrect: psychological interventions versus waiting list; psychological interventions versus placebo; psychological interventions versus usual care.\n"
        "- Correct: antidepressants versus active comparator. Incorrect: antidepressants versus fluoxetine; antidepressants versus sertraline when the review only reports an active-comparator family.\n"
        "- Correct: exercise versus usual care or no treatment. Incorrect: exercise versus usual care and exercise versus no treatment as separate outputs when the review synthesizes the grouped family.\n"
        "- Correct: [] when no supported comparison can be recovered. Incorrect: infer a comparison from subgroup labels, timepoints, or unsupported arm names alone."
    )


def _build_payload(
    instance: dict[str, Any],
    *,
    evidence_strategy: str,
    decision_strategy: str,
) -> dict[str, Any]:
    data_type = instance.get("task_metadata", {}).get("condition_data_type", "")
    payload = {
        "review_id": instance.get("review_id"),
        "review_title": instance.get("sr_title"),
        "sr_pico": instance.get("sr_pico", {}),
        "outcome_concept": instance.get("outcome_concept", ""),
        "task_metadata": instance.get("task_metadata", {}),
        "study_evidence": _render_study_evidence(
            instance.get("study_evidence", []),
            task_name=instance.get("task_name", ""),
            evidence_strategy=evidence_strategy,
            condition_data_type=data_type,
        ),
    }
    if instance.get("task_name") == EFFECT_MEASURE_TASK:
        payload["allowed_effect_measures"] = get_effect_measure_selection_options(data_type)
        payload["effect_measure_selection_guidance"] = get_effect_measure_selection_guidance(data_type)
        payload["condition_data_type"] = data_type
        payload["evidence_strategy"] = evidence_strategy
        payload["decision_strategy"] = decision_strategy
    if instance.get("task_name") == COMPARISONS_TASK and decision_strategy == "constrained_selection":
        payload["comparison_candidates"] = (
            instance.get("task_metadata", {}).get("comparison_candidates")
            or build_comparison_candidates(instance)
        )
        payload["decision_strategy"] = decision_strategy
    return payload


def build_conditional_prompt(
    instance: dict[str, Any],
    *,
    prompt_version: str | None = None,
    evidence_strategy: str = DEFAULT_EVIDENCE_STRATEGY,
    decision_strategy: str = DEFAULT_DECISION_STRATEGY,
    few_shot_set: str | None = None,
) -> str:
    task_name = instance["task_name"]
    spec = get_conditional_task_spec(task_name)
    resolved_prompt_version = prompt_version or CONDITIONAL_PROMPT_VERSION
    prompt_spec = get_prompt_spec(resolved_prompt_version)
    template = _read_text(prompt_spec.prompt_template_path)
    data_type = instance.get("task_metadata", {}).get("condition_data_type", "")
    selection_options = get_effect_measure_selection_options(data_type) if task_name == EFFECT_MEASURE_TASK else []
    selection_guidance = get_effect_measure_selection_guidance(data_type) if task_name == EFFECT_MEASURE_TASK else []
    if task_name == COMPARISONS_TASK and decision_strategy == "constrained_selection":
        selection_options = instance.get("task_metadata", {}).get("comparison_candidates") or build_comparison_candidates(instance)
        selection_guidance = [
            "Choose zero or more candidate comparisons that are explicitly supported at the review level for this outcome.",
            "Copy selected comparison labels exactly as they appear in the candidate list.",
            "Prefer grouped family labels when the review synthesizes grouped families instead of enumerating atomic pairs.",
        ]
    task_instructions = spec.instructions + _comparison_branch_instructions(task_name, resolved_prompt_version, decision_strategy)
    return template.format(
        prompt_version=prompt_spec.version,
        task_name=task_name,
        task_label=spec.prompt_label,
        task_instructions=task_instructions,
        condition_data_type=data_type,
        evidence_strategy=evidence_strategy,
        decision_strategy=decision_strategy,
        output_schema_json=json.dumps(spec.output_schema, ensure_ascii=False, indent=2),
        input_payload_json=json.dumps(
            _build_payload(
                instance,
                evidence_strategy=evidence_strategy,
                decision_strategy=decision_strategy,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        selection_options_json=json.dumps(selection_options, ensure_ascii=False, indent=2),
        selection_guidance_text="\n".join(f"- {item}" for item in selection_guidance),
        few_shots_section=_few_shots_section(resolved_prompt_version, few_shot_set),
    )
