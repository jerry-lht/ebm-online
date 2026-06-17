"""Deterministic indirectness GRADE domain method."""

from __future__ import annotations

from typing import Any

from ebm_backend.online_pipeline.infrastructure.methods.grade.base import GradeDomainMethod
from ebm_backend.online_pipeline.infrastructure.methods.grade.common import (
    as_list,
    first_dict,
    join_text,
    norm_text,
    not_serious,
    serious,
    token_overlap,
    unclear,
)


DOMAIN = "indirectness"


class Method(GradeDomainMethod):
    domain = DOMAIN

    def run(self, *, domain_evidence: dict[str, Any], evidence_body: dict[str, Any]) -> dict[str, Any]:
        return predict(domain_evidence=domain_evidence, evidence_body=evidence_body)


def predict(*, domain_evidence: dict[str, Any], evidence_body: dict[str, Any]) -> dict[str, Any]:
    target = first_dict(domain_evidence.get("target_pico"))
    setting = first_dict(domain_evidence.get("analysis_setting"), evidence_body.get("analysis_setting"))
    screening_criteria = first_dict(domain_evidence.get("screening_criteria"))
    characteristics = as_list(domain_evidence.get("study_characteristics"))
    missing = as_list(domain_evidence.get("study_characteristics_missing_study_ids"))
    sof_context = first_dict(evidence_body.get("sof_context"), domain_evidence.get("sof_context"))

    target_text = join_text(
        target.get("population_text"),
        target.get("setting_text"),
        target.get("intervention_text"),
        target.get("comparison_text"),
        target.get("outcome_text"),
        target.get("timepoint_text"),
        join_text(*(screening_criteria.get("inclusion_criteria") or [])),
        join_text(*(screening_criteria.get("exclusion_criteria") or [])),
        screening_criteria.get("rationale"),
        sof_context.get("population_text"),
        sof_context.get("setting_text"),
    )
    setting_text = join_text(
        (setting.get("comparison") or {}).get("text"),
        (setting.get("outcome") or {}).get("label"),
        (setting.get("timepoint") or {}).get("label"),
        (setting.get("subgroup") or {}).get("level"),
    )
    study_text = join_text(
        *[
            join_text(item.get("population"), item.get("intervention_comparator"), item.get("outcomes"), item.get("methods"))
            for item in characteristics
            if isinstance(item, dict)
        ]
    )
    all_text = norm_text(join_text(target_text, setting_text, study_text))
    if not characteristics and missing:
        return unclear(DOMAIN, "Study characteristics are missing for contributing studies.")
    indirect_terms = (
        "proxy",
        "surrogate",
        "indirect",
        "different population",
        "different comparator",
        "different outcome",
        "different setting",
        "post hoc",
    )
    if any(term.replace(" ", "_") in all_text or term in all_text for term in indirect_terms):
        return serious(DOMAIN, "Evidence text contains direct signals of indirectness.")
    if setting_text and target_text and token_overlap(setting_text, target_text) < 0.10:
        return serious(DOMAIN, "Selected analysis setting has low textual overlap with the target SoF context.")
    if missing:
        return unclear(DOMAIN, "Study-characteristics evidence is incomplete for part of the evidence body.")
    return not_serious(DOMAIN, "Analysis setting and available study characteristics appear directly applicable.")


def build_method() -> Method:
    return Method()
