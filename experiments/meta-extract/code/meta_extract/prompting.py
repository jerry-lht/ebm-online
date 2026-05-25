"""Prompt strategy registry and builders for benchmark2-v2 tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .constants import DIRECT_FIELDS_BY_DATA_TYPE
from .normalize import normalize_phrase, normalize_text_loose

PROMPT_VERSION = "benchmark2-v2"
PROMPT_ROOT = Path(__file__).resolve().parent / "prompts"
DATA_TYPE_PROMPT_KEY = {
    "Dichotomous": "dichotomous",
    "Continuous": "continuous",
    "Contrast level": "contrast_level",
    "__default__": "__default__",
}

PayloadBuilder = Callable[[dict, str | None, list[dict], list[dict], list[str]], dict]
ContextBuilder = Callable[[dict, int, int], tuple[list[dict], list[dict], dict]]


@dataclass(frozen=True)
class PromptStrategy:
    task_name: str
    variant: str
    section_limit: int
    table_limit: int
    shared_rules: tuple[str, ...]
    data_type_rules: dict[str, tuple[str, ...]]
    payload_builder: PayloadBuilder
    context_builder: ContextBuilder | None = None


@dataclass(frozen=True)
class PromptBundle:
    task_name: str
    variant: str
    data_type: str | None
    messages: list[dict]
    context_stats: dict
    allowed_fields: list[str]

    @property
    def prompt_name(self) -> str:
        return f"{self.task_name}:{self.variant}"


def _load_rule_file(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    return tuple(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _prompt_rule_set(task_name: str, variant: str) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    base = PROMPT_ROOT / task_name / variant
    shared_rules = _load_rule_file(base / "shared.txt")
    data_type_rules = {}
    for data_type, prompt_key in DATA_TYPE_PROMPT_KEY.items():
        rule_path = base / f"{prompt_key}.txt"
        if rule_path.exists():
            data_type_rules[data_type] = _load_rule_file(rule_path)
    return shared_rules, data_type_rules


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _keyword_terms(*values: Any) -> list[str]:
    terms = []
    seen = set()
    for value in values:
        if isinstance(value, list):
            terms.extend(_keyword_terms(*value))
            continue
        if isinstance(value, dict):
            terms.extend(_keyword_terms(*value.values()))
            continue
        text = normalize_text_loose(value)
        if len(text) < 3 or text in seen:
            continue
        seen.add(text)
        terms.append(text)
    return terms


def _section_terms(instance: dict) -> list[str]:
    setting = instance.get("setting_context") or {}
    item = instance.get("official_item") or {}
    return _keyword_terms(
        setting.get("outcome_concept"),
        setting.get("comparison"),
        setting.get("effect_measure"),
        setting.get("subgroup_candidates"),
        setting.get("timepoints"),
        setting.get("reported_outcome_measures"),
        item.get("subgroup"),
        item.get("timepoints"),
    )


def _dedupe_text_values(value_list: list[Any]) -> list[Any]:
    deduped = []
    seen = set()
    for value in value_list:
        key = normalize_phrase(value)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _filter_relevant_text_values(values: list[Any], targets: list[Any]) -> list[Any]:
    target_terms = [normalize_phrase(target) for target in targets if normalize_phrase(target)]
    if not target_terms:
        return []
    matched = []
    for value in values or []:
        haystack = normalize_phrase(value)
        if not haystack:
            continue
        if any(term in haystack or haystack in term for term in target_terms):
            matched.append(value)
    return _dedupe_text_values(matched)


def _oracle_setting_context_slice(instance: dict) -> dict:
    setting = instance.get("setting_context") or {}
    item = instance.get("official_item") or {}
    comparison = item.get("comparison") or setting.get("comparison")
    subgroup = item.get("subgroup")
    timepoints = item.get("timepoints") or []
    reported_outcome_measures = setting.get("reported_outcome_measures") or []
    filtered_measures = _filter_relevant_text_values(
        reported_outcome_measures,
        [comparison, subgroup, *timepoints],
    )
    filtered_subgroups = _filter_relevant_text_values(
        setting.get("subgroup_candidates") or [],
        [subgroup],
    )
    return {
        "data_type": setting.get("data_type"),
        "effect_measure": setting.get("effect_measure"),
        "comparison": comparison,
        "arm_pairs": setting.get("arm_pairs") or [],
        "reported_outcome_measures": filtered_measures or reported_outcome_measures,
        "subgroup_candidates": filtered_subgroups,
        "timepoints": _dedupe_text_values(list(timepoints)),
    }


def _score_block(block: dict, terms: list[str]) -> int:
    haystack = normalize_text_loose(_flatten_text(block))
    return sum(term in haystack for term in terms)


def _select_context_blocks(blocks: list[dict], terms: list[str], limit: int) -> list[dict]:
    if not blocks:
        return []
    scored = [(_score_block(block, terms), index, block) for index, block in enumerate(blocks)]
    matched = [entry for entry in scored if entry[0] > 0]
    chosen = matched if matched else scored
    chosen.sort(key=lambda entry: (-entry[0], entry[1]))
    return [entry[2] for entry in chosen[:limit]]


def _build_context_slice(instance: dict, *, section_limit: int, table_limit: int) -> tuple[list[dict], list[dict], dict]:
    full_content = (instance.get("study") or {}).get("full_content") or {}
    terms = _section_terms(instance)
    sections = _select_context_blocks(full_content.get("sections") or [], terms, section_limit)
    tables = _select_context_blocks(full_content.get("tables") or [], terms, table_limit)
    return sections, tables, {"section_count": len(sections), "table_count": len(tables)}


def _is_abstract_or_results_section(block: dict) -> bool:
    label = normalize_phrase(block.get("section") or block.get("heading") or "")
    if not label:
        return False
    return "abstract" in label or "result" in label


def _build_results_context_slice(instance: dict, section_limit: int, table_limit: int) -> tuple[list[dict], list[dict], dict]:
    full_content = (instance.get("study") or {}).get("full_content") or {}
    terms = _section_terms(instance)
    candidate_sections = [block for block in (full_content.get("sections") or []) if _is_abstract_or_results_section(block)]
    sections = _select_context_blocks(candidate_sections, terms, section_limit)
    tables = _select_context_blocks(full_content.get("tables") or [], terms, table_limit)
    return sections, tables, {"section_count": len(sections), "table_count": len(tables), "section_filter": "abstract_or_results"}


def _support_output_schema(target: str) -> dict:
    base_reasons = [
        "insufficient_evidence",
        "timepoint_granularity_mismatch",
        "multiple_plausible_interpretations",
    ]
    if target == "subgroup":
        return {
            "subgroup_support_status": "supported | not_supported | uncertain",
            "uncertain_reasons": base_reasons,
        }
    if target == "timepoint":
        return {
            "timepoint_support_status": "supported | not_supported | uncertain",
            "uncertain_reasons": base_reasons,
        }
    return {
        "subgroup_support_status": "supported | not_supported | uncertain",
        "timepoint_support_status": "supported | not_supported | uncertain",
        "uncertain_reasons": base_reasons,
    }


def _build_support_payload(instance: dict, data_type: str | None, sections: list[dict], tables: list[dict], allowed_fields: list[str], *, target: str = "joint") -> dict:
    del data_type, allowed_fields
    return {
        "study": instance["study"],
        "setting_context": instance["setting_context"],
        "official_item": instance["official_item"],
        "evidence_sections": sections,
        "evidence_tables": tables,
        "support_target": target,
        "output_schema": _support_output_schema(target),
    }


def _proposal_output_schema(target: str) -> dict:
    if target == "subgroup":
        return {"proposed_subgroups": ["string|null"]}
    if target == "timepoint":
        return {"proposed_timepoints": ["string"]}
    return {"proposed_items": [{"subgroup": "string|null", "timepoints": ["string"]}]}


def _build_proposal_payload(instance: dict, data_type: str | None, sections: list[dict], tables: list[dict], allowed_fields: list[str], *, target: str = "joint") -> dict:
    del data_type, allowed_fields
    return {
        "study": instance["study"],
        "setting_context": instance["setting_context"],
        "evidence_sections": sections,
        "evidence_tables": tables,
        "proposal_target": target,
        "output_schema": _proposal_output_schema(target),
    }


def _build_oracle_extraction_payload(instance: dict, data_type: str | None, sections: list[dict], tables: list[dict], allowed_fields: list[str]) -> dict:
    return {
        "study": instance["study"],
        "setting_context": _oracle_setting_context_slice(instance),
        "official_item": instance["official_item"],
        "task_target": {
            "unit": "official_item",
            "instruction": "Return all and only direct extraction rows for this official item. Use setting_context only as auxiliary disambiguation context.",
        },
        "allowed_direct_fields": allowed_fields,
        "evidence_sections": sections,
        "evidence_tables": tables,
        "output_schema": {
            "predicted_rows": [{"direct_extraction_fields": [{"field": allowed_fields[0] if allowed_fields else "Experimental mean", "value": "string"}]}]
        },
    }


def _build_routed_extraction_payload(instance: dict, data_type: str | None, sections: list[dict], tables: list[dict], allowed_fields: list[str]) -> dict:
    return {
        "study": instance["study"],
        "setting_context": instance["setting_context"],
        "allowed_direct_fields": allowed_fields,
        "evidence_sections": sections,
        "evidence_tables": tables,
        "output_schema": {
            "predicted_items": [
                {
                    "subgroup": "string|null",
                    "timepoints": ["string"],
                    "predicted_rows": [{"direct_extraction_fields": [{"field": allowed_fields[0] if allowed_fields else "Experimental mean", "value": "string"}]}],
                }
            ]
        },
    }


def _allowed_fields_for(data_type: str | None) -> list[str]:
    return list(DIRECT_FIELDS_BY_DATA_TYPE.get(data_type or "", []))


def _render_system_prompt(shared_rules: tuple[str, ...], type_rules: tuple[str, ...]) -> str:
    parts = [*shared_rules, *type_rules]
    if not parts:
        parts = ("Return strict JSON only.",)
    return "\n".join(parts)


PROMPT_STRATEGIES: dict[tuple[str, str], PromptStrategy] = {}


def register_prompt_strategy(strategy: PromptStrategy, *, replace: bool = False) -> None:
    key = (strategy.task_name, strategy.variant)
    if key in PROMPT_STRATEGIES and not replace:
        raise ValueError(f"Prompt strategy already registered: {key}")
    PROMPT_STRATEGIES[key] = strategy


def get_prompt_strategy(task_name: str, variant: str = "default") -> PromptStrategy:
    try:
        return PROMPT_STRATEGIES[(task_name, variant)]
    except KeyError as exc:
        raise ValueError(f"Unknown prompt strategy: task_name={task_name!r}, variant={variant!r}") from exc


def available_prompt_variants(task_name: str) -> list[str]:
    return sorted(variant for current_task, variant in PROMPT_STRATEGIES if current_task == task_name)


def build_prompt_bundle(task_name: str, instance: dict, *, variant: str = "default", extra_system_rules: tuple[str, ...] = (), payload_override: dict | None = None) -> PromptBundle:
    strategy = get_prompt_strategy(task_name, variant)
    data_type = (instance.get("setting_context") or {}).get("data_type")
    context_builder = strategy.context_builder or (lambda current_instance, current_section_limit, current_table_limit: _build_context_slice(current_instance, section_limit=current_section_limit, table_limit=current_table_limit))
    sections, tables, context_stats = context_builder(instance, strategy.section_limit, strategy.table_limit)
    allowed_fields = _allowed_fields_for(data_type) if task_name in {"oracle_extraction", "routed_extraction"} else []
    payload = payload_override if payload_override is not None else strategy.payload_builder(instance, data_type, sections, tables, allowed_fields)
    type_rules = strategy.data_type_rules.get(data_type or "", strategy.data_type_rules.get("__default__", ()))
    messages = [
        {"role": "system", "content": _render_system_prompt(strategy.shared_rules + extra_system_rules, type_rules)},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
    ]
    return PromptBundle(
        task_name=task_name,
        variant=variant,
        data_type=data_type,
        messages=messages,
        context_stats={**context_stats, "allowed_field_count": len(allowed_fields)},
        allowed_fields=allowed_fields,
    )


def build_support_prompt_bundle(instance: dict, *, variant: str = "default", target: str = "joint") -> PromptBundle:
    data_type = (instance.get("setting_context") or {}).get("data_type")
    strategy = get_prompt_strategy("support", variant)
    sections, tables, _ = _build_context_slice(instance, section_limit=strategy.section_limit, table_limit=strategy.table_limit)
    payload = _build_support_payload(instance, data_type, sections, tables, [], target=target)
    extra_rules = ()
    if target == "subgroup":
        extra_rules = (
            "Only decide subgroup_support_status and uncertain_reasons for subgroup support.",
            "Do not infer or output timepoint support in this call.",
        )
    elif target == "timepoint":
        extra_rules = (
            "Only decide timepoint_support_status and uncertain_reasons for timepoint support.",
            "Do not infer or output subgroup support in this call.",
            "Count official timepoint as supported when the result itself is explicitly tied to that follow-up phrase, endpoint window, visit label, row label, outcome label, or row-specific note after normalization.",
            "A timepoint can still be supported when it appears in the outcome label or table row for the reported result, even if the same sentence does not restate it next to every number.",
            "Do not require the article to repeat the exact same wording if the normalized timepoint clearly matches the reported result timing.",
            "Still do not treat generic study duration, generic visit schedules, or background follow-up descriptions as support unless they are clearly attached to the reported result.",
        )
    return build_prompt_bundle("support", instance, variant=variant, extra_system_rules=extra_rules, payload_override=payload)


def build_proposal_prompt_bundle(instance: dict, *, variant: str = "default", target: str = "joint") -> PromptBundle:
    data_type = (instance.get("setting_context") or {}).get("data_type")
    strategy = get_prompt_strategy("proposal", variant)
    sections, tables, _ = _build_context_slice(instance, section_limit=strategy.section_limit, table_limit=strategy.table_limit)
    payload = _build_proposal_payload(instance, data_type, sections, tables, [], target=target)
    extra_rules = ()
    if target == "subgroup":
        extra_rules = (
            "Only propose valid subgroup distinctions for this setting.",
            "Return proposed_subgroups only; do not output timepoints in this call.",
            "Use subgroup = null only when the setting is not subgroup-defined after applying the benchmark rules.",
            "Prioritize explicit subgroup candidates already surfaced in setting_context.subgroup_candidates when they are supported by the evidence.",
        )
    elif target == "timepoint":
        extra_rules = (
            "Only propose valid timepoint distinctions for this setting.",
            "Return proposed_timepoints only; do not output subgroup values in this call.",
            "Treat a timepoint as valid only when it defines the analysis item itself, not when it is merely a generic study duration, visit schedule, or background follow-up description.",
            "Prioritize explicit timepoint candidates already surfaced in setting_context.timepoints and row- or outcome-level timing labels tied to the reported result.",
        )
    return build_prompt_bundle("proposal", instance, variant=variant, extra_system_rules=extra_rules, payload_override=payload)


def build_oracle_extraction_prompt_bundle(instance: dict, *, variant: str = "default") -> PromptBundle:
    return build_prompt_bundle("oracle_extraction", instance, variant=variant)


def build_routed_extraction_prompt_bundle(instance: dict, *, variant: str = "default") -> PromptBundle:
    return build_prompt_bundle("routed_extraction", instance, variant=variant)


for task_name, section_limit, table_limit, builder in (
    ("support", 8, 4, _build_support_payload),
    ("proposal", 8, 4, _build_proposal_payload),
    ("oracle_extraction", 10, 6, _build_oracle_extraction_payload),
    ("routed_extraction", 10, 6, _build_routed_extraction_payload),
):
    shared_rules, data_type_rules = _prompt_rule_set(task_name, "default")
    register_prompt_strategy(
        PromptStrategy(
            task_name=task_name,
            variant="default",
            section_limit=section_limit,
            table_limit=table_limit,
            shared_rules=shared_rules,
            data_type_rules=data_type_rules,
            payload_builder=builder,
        )
    )

shared_rules, data_type_rules = _prompt_rule_set("oracle_extraction", "few_shot")
register_prompt_strategy(
    PromptStrategy(
        task_name="oracle_extraction",
        variant="few_shot",
        section_limit=12,
        table_limit=10,
        shared_rules=shared_rules,
        data_type_rules=data_type_rules,
        payload_builder=_build_oracle_extraction_payload,
    )
)

shared_rules, data_type_rules = _prompt_rule_set("oracle_extraction", "default")
register_prompt_strategy(
    PromptStrategy(
        task_name="oracle_extraction",
        variant="results_slice",
        section_limit=8,
        table_limit=10,
        shared_rules=shared_rules,
        data_type_rules=data_type_rules,
        payload_builder=_build_oracle_extraction_payload,
        context_builder=_build_results_context_slice,
    )
)

shared_rules, data_type_rules = _prompt_rule_set("oracle_extraction", "few_shot")
register_prompt_strategy(
    PromptStrategy(
        task_name="oracle_extraction",
        variant="results_slice_few_shot",
        section_limit=8,
        table_limit=10,
        shared_rules=shared_rules,
        data_type_rules=data_type_rules,
        payload_builder=_build_oracle_extraction_payload,
        context_builder=_build_results_context_slice,
    )
)

for variant in ("negative_examples", "negative_examples_ebm", "negative_examples_split"):
    shared_rules, data_type_rules = _prompt_rule_set("proposal", variant)
    register_prompt_strategy(
        PromptStrategy(
            task_name="proposal",
            variant=variant,
            section_limit=8,
            table_limit=4,
            shared_rules=shared_rules,
            data_type_rules=data_type_rules,
            payload_builder=_build_proposal_payload,
        )
    )
