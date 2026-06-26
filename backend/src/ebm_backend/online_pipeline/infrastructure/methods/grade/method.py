"""GRADE module-level method coordinator."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ebm_backend.online_pipeline.domain.common import GradeDomainName
from ebm_backend.online_pipeline.domain.grade import (
    DomainJudgements,
    EffectEstimateRef,
    GRADEDomainJudgement,
    GradeResult,
    SoFRowGRADEAssessment,
)
from ebm_backend.online_pipeline.domain.meta_analysis import MetaAnalysisResultPackage
from ebm_backend.online_pipeline.domain.question import QuestionPICO
from ebm_backend.online_pipeline.domain.risk_of_bias import RiskOfBiasAssessment
from ebm_backend.online_pipeline.domain.screening import ScreeningCriteria
from ebm_backend.online_pipeline.domain.study_characteristics import StudyPIOCharacteristics
from ebm_backend.online_pipeline.domain.serialization import to_jsonable
from ebm_backend.online_pipeline.infrastructure.methods.grade.base import GradeAssessmentMethod
from ebm_backend.online_pipeline.infrastructure.methods.grade.common import unclear
from ebm_backend.online_pipeline.infrastructure.methods.grade.loader import GRADE_DOMAIN_NAMES, get_grade_domain_method


class Method(GradeAssessmentMethod):
    """Coordinate four independently implemented GRADE domain methods."""

    def __init__(self, *, domain_method_name: str = "method_test") -> None:
        self.domain_method_name = domain_method_name
        self.domain_methods: dict[str, Any] = {}

    def run_instance(self, *, instance: dict[str, Any]) -> dict[str, Any]:
        domain = str(instance.get("domain") or "")
        if domain not in GRADE_DOMAIN_NAMES:
            judgement = unclear(domain or "unknown", "Unsupported GRADE domain.")
        else:
            domain_method = self._domain_method(domain)
            judgement = domain_method.run(
                domain_evidence=_dict_value(instance.get("domain_evidence")),
                evidence_body=_dict_value(instance.get("evidence_body")),
            )
        return {
            "instance_id": instance.get("instance_id"),
            "sof_row_id": instance.get("sof_row_id"),
            "review_id": instance.get("review_id"),
            "domain": instance.get("domain"),
            "judgement": judgement,
        }

    def _domain_method(self, domain: str):
        if domain not in self.domain_methods:
            self.domain_methods[domain] = get_grade_domain_method(domain, self.domain_method_name)
        return self.domain_methods[domain]

    def run(
        self,
        *,
        review_id: str,
        question_text: str,
        question_pico: QuestionPICO,
        screening_criteria: ScreeningCriteria,
        study_characteristics: list[StudyPIOCharacteristics],
        risk_of_bias: list[RiskOfBiasAssessment],
        meta_analysis_result: MetaAnalysisResultPackage,
    ) -> GradeResult:
        rows = []
        for setting in meta_analysis_result.analysis_settings:
            estimate_type, estimate = _matched_estimate(setting=setting, meta_analysis_result=meta_analysis_result)
            if estimate is None:
                continue
            included_study_ids = list(estimate.included_study_ids)
            filtered_study_characteristics = [
                item for item in study_characteristics if item.study_id in set(included_study_ids)
            ]
            filtered_risk_of_bias = [item for item in risk_of_bias if item.study_id in set(included_study_ids)]
            missing_study_characteristics_ids = [
                study_id for study_id in included_study_ids if study_id not in {item.study_id for item in filtered_study_characteristics}
            ]
            missing_risk_of_bias_ids = [
                study_id for study_id in included_study_ids if study_id not in {item.study_id for item in filtered_risk_of_bias}
            ]
            evidence_body = _workflow_evidence_body(
                setting=setting,
                estimate=estimate,
                estimate_type=estimate_type,
                meta_analysis_result=meta_analysis_result,
                question_pico=question_pico,
                screening_criteria=screening_criteria,
                study_characteristics=filtered_study_characteristics,
                risk_of_bias=filtered_risk_of_bias,
                missing_study_characteristics_ids=missing_study_characteristics_ids,
                missing_risk_of_bias_ids=missing_risk_of_bias_ids,
            )
            row_context = {
                "instance_id": f"workflow-grade::{review_id}::{setting.setting_id}",
                "review_id": review_id,
                "sof_row_id": f"sof-row::{setting.setting_id}",
                "question_text": question_text,
                "question_pico": to_jsonable(question_pico),
                "screening_criteria": to_jsonable(screening_criteria),
                "evidence_body": evidence_body,
                "alignment": {},
            }
            judgements = {
                domain: self.run_instance(instance={**row_context, "domain": domain, "domain_evidence": _domain_evidence(evidence_body=evidence_body, domain=domain)})[
                    "judgement"
                ]
                for domain in sorted(GRADE_DOMAIN_NAMES)
            }
            rows.append(
                SoFRowGRADEAssessment(
                    sof_row_id=str(row_context["sof_row_id"]),
                    row_label=setting.outcome.label,
                    setting_id=setting.setting_id,
                    setting_family_id=setting.setting_family_id,
                    candidate_id=setting.candidate_id,
                    comparison=setting.comparison,
                    outcome=setting.outcome,
                    timepoint=setting.timepoint,
                    subgroup=setting.subgroup,
                    effect_estimate_ref=EffectEstimateRef(
                        estimate_type=estimate_type,
                        estimate_id=_estimate_id(estimate=estimate, estimate_type=estimate_type),
                        estimation_status=str(estimate.estimation_status),
                    ),
                    included_study_ids=list(estimate.included_study_ids),
                    domain_judgements=DomainJudgements(
                        risk_of_bias=_dataclass_judgement(judgements["risk_of_bias"], GradeDomainName.RISK_OF_BIAS),
                        inconsistency=_dataclass_judgement(judgements["inconsistency"], GradeDomainName.INCONSISTENCY),
                        indirectness=_dataclass_judgement(judgements["indirectness"], GradeDomainName.INDIRECTNESS),
                        imprecision=_dataclass_judgement(judgements["imprecision"], GradeDomainName.IMPRECISION),
                    ),
                )
            )
        return GradeResult(review_id=review_id, question_text=question_text, sof_rows=rows)


def _matched_estimate(*, setting, meta_analysis_result) -> tuple[str, Any | None]:
    if setting.subgroup.is_overall:
        for estimate in meta_analysis_result.overall_estimates:
            if estimate.setting_id == setting.setting_id:
                return "overall", estimate
        return "overall", None
    for estimate in meta_analysis_result.subgroup_estimates:
        if estimate.setting_id == setting.setting_id:
            return "subgroup", estimate
    return "subgroup", None


def _workflow_evidence_body(
    *,
    setting,
    estimate,
    estimate_type: str,
    meta_analysis_result,
    question_pico: QuestionPICO,
    screening_criteria: ScreeningCriteria,
    study_characteristics: list[StudyPIOCharacteristics],
    risk_of_bias: list[RiskOfBiasAssessment],
    missing_study_characteristics_ids: list[str],
    missing_risk_of_bias_ids: list[str],
) -> dict[str, Any]:
    included = set(estimate.included_study_ids)
    study_rows = [
        to_jsonable(row)
        for row in meta_analysis_result.study_result_rows
        if row.setting_id == setting.setting_id and row.study_id in included
    ]
    return {
        "setting_id": setting.setting_id,
        "setting_family_id": setting.setting_family_id,
        "candidate_id": setting.candidate_id,
        "analysis_setting": to_jsonable(setting),
        "target_pico": to_jsonable(question_pico),
        "screening_criteria": to_jsonable(screening_criteria),
        "effect_estimate_ref": {
            "estimate_type": estimate_type,
            "estimate_id": _estimate_id(estimate=estimate, estimate_type=estimate_type),
            "estimation_status": str(estimate.estimation_status),
        },
        "effect_estimate": to_jsonable(estimate),
        "included_study_ids": list(estimate.included_study_ids),
        "study_characteristics": [to_jsonable(item) for item in study_characteristics],
        "study_characteristics_missing_study_ids": list(missing_study_characteristics_ids),
        "risk_of_bias_assessments": [to_jsonable(item) for item in risk_of_bias],
        "risk_of_bias_missing_study_ids": list(missing_risk_of_bias_ids),
        "study_result_rows": study_rows,
        "subgroup_estimates": [to_jsonable(row) for row in meta_analysis_result.subgroup_estimates if row.setting_family_id == setting.setting_family_id],
        "subgroup_difference_tests": [
            to_jsonable(row)
            for row in meta_analysis_result.subgroup_difference_tests
            if row.setting_family_id == setting.setting_family_id
        ],
    }


def _domain_evidence(*, evidence_body: dict[str, Any], domain: str) -> dict[str, Any]:
    estimate = _dict_value(evidence_body.get("effect_estimate"))
    if domain == "risk_of_bias":
        return {
            "included_study_ids": evidence_body.get("included_study_ids") or [],
            "risk_of_bias_assessments": evidence_body.get("risk_of_bias_assessments") or [],
            "risk_of_bias_missing_study_ids": evidence_body.get("risk_of_bias_missing_study_ids") or [],
        }
    if domain == "indirectness":
        return {
            "analysis_setting": evidence_body.get("analysis_setting") or {},
            "included_study_ids": evidence_body.get("included_study_ids") or [],
            "screening_criteria": evidence_body.get("screening_criteria") or {},
            "study_characteristics": evidence_body.get("study_characteristics") or [],
            "study_characteristics_missing_study_ids": evidence_body.get("study_characteristics_missing_study_ids") or [],
            "target_pico": evidence_body.get("target_pico") or {},
        }
    if domain == "inconsistency":
        return {
            "effect_estimate": estimate,
            "heterogeneity": estimate.get("heterogeneity") if isinstance(estimate, dict) else {},
            "subgroup_estimates": evidence_body.get("subgroup_estimates") or [],
            "subgroup_difference_tests": evidence_body.get("subgroup_difference_tests") or [],
            "study_result_rows": evidence_body.get("study_result_rows") or [],
            "included_study_ids": evidence_body.get("included_study_ids") or [],
        }
    return {
        "effect_estimate": estimate,
        "study_result_rows": evidence_body.get("study_result_rows") or [],
        "study_count": estimate.get("study_count") if isinstance(estimate, dict) else None,
        "participant_count": estimate.get("participant_count") if isinstance(estimate, dict) else None,
        "data_type": estimate.get("data_type") if isinstance(estimate, dict) else None,
        "effect_measure": estimate.get("effect_measure") if isinstance(estimate, dict) else None,
    }


def _dataclass_judgement(payload: dict[str, Any], domain: GradeDomainName) -> GRADEDomainJudgement:
    return GRADEDomainJudgement(
        domain=domain,
        downgraded=str(payload.get("downgraded") or "unclear"),
        severity=str(payload.get("severity") or "unclear"),
        levels=payload.get("levels", "unclear"),
        level_evaluable=bool(payload.get("level_evaluable")),
        rationale=str(payload.get("rationale") or ""),
        source_spans=[],
    )


def _estimate_id(*, estimate, estimate_type: str) -> str | None:
    return getattr(estimate, "overall_estimate_id", None) if estimate_type == "overall" else getattr(estimate, "subgroup_estimate_id", None)


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_method(method_name: str = "method_test") -> Method:
    return Method(domain_method_name=method_name)
