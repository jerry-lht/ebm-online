"""Deterministic inconsistency GRADE domain method."""

from __future__ import annotations

from typing import Any

from ebm_backend.online_pipeline.infrastructure.methods.grade.base import GradeDomainMethod
from ebm_backend.online_pipeline.infrastructure.methods.grade.common import (
    as_float,
    as_list,
    ci_crosses_line_of_no_effect,
    first_dict,
    not_serious,
    serious,
)


DOMAIN = "inconsistency"


class Method(GradeDomainMethod):
    domain = DOMAIN

    def run(self, *, domain_evidence: dict[str, Any], evidence_body: dict[str, Any]) -> dict[str, Any]:
        return predict(domain_evidence=domain_evidence, evidence_body=evidence_body)


def predict(*, domain_evidence: dict[str, Any], evidence_body: dict[str, Any]) -> dict[str, Any]:
    estimate = first_dict(domain_evidence.get("effect_estimate"), evidence_body.get("effect_estimate"))
    heterogeneity = first_dict(domain_evidence.get("heterogeneity"), estimate.get("heterogeneity"))
    i2 = as_float(heterogeneity.get("i2"))
    p_value = as_float(heterogeneity.get("p_value"))
    prediction_interval = first_dict(estimate.get("prediction_interval"))
    subgroup_tests = as_list(domain_evidence.get("subgroup_difference_tests") or evidence_body.get("subgroup_difference_tests"))
    study_rows = as_list(domain_evidence.get("study_result_rows") or evidence_body.get("study_result_rows"))

    important_subgroup_test = any(
        (as_float(row.get("p_value")) is not None and as_float(row.get("p_value")) < 0.05)
        for row in subgroup_tests
        if isinstance(row, dict)
    )
    if i2 is not None and i2 >= 75:
        return serious(DOMAIN, "I-squared is very high for the evidence body.")
    if important_subgroup_test:
        return serious(DOMAIN, "Subgroup difference testing suggests important unexplained inconsistency.")
    if i2 is not None and i2 >= 50:
        return serious(DOMAIN, "I-squared suggests substantial heterogeneity.")
    if p_value is not None and p_value < 0.10 and len(study_rows) >= 2:
        return serious(DOMAIN, "Chi-squared heterogeneity test is suggestive with multiple studies.")
    if _prediction_interval_crosses_line_of_no_effect(prediction_interval, estimate):
        return serious(DOMAIN, "Prediction interval crosses the line of no effect.")
    return not_serious(DOMAIN, "No important heterogeneity signal was available.")


def _prediction_interval_crosses_line_of_no_effect(prediction_interval: dict[str, Any], estimate: dict[str, Any]) -> bool:
    lower = as_float(prediction_interval.get("lower"))
    upper = as_float(prediction_interval.get("upper"))
    if lower is None or upper is None:
        return False
    return ci_crosses_line_of_no_effect(lower, upper, str(estimate.get("effect_measure") or ""))


def build_method() -> Method:
    return Method()
