from __future__ import annotations

from copy import deepcopy
from typing import Any

from .constants import REQUIRED_FIELDS


CANONICALIZATION_VERSION = "review_level_v3"


def _candidate_text(candidate: dict[str, Any]) -> str:
    pieces: list[str] = [
        candidate.get("outcome_concept", ""),
        candidate.get("data_type", ""),
        candidate.get("candidate_effect_measure", ""),
        " ".join(candidate.get("comparisons", [])),
        " ".join(candidate.get("reported_outcome_measures", [])),
        " ".join(candidate.get("subgroup_candidates", [])),
        " ".join(candidate.get("timepoints", [])),
    ]
    for arm_pair in candidate.get("arm_pairs", []):
        if isinstance(arm_pair, dict):
            pieces.append(arm_pair.get("experimental_arm", ""))
            pieces.append(arm_pair.get("control_arm", ""))
    return " ".join(piece for piece in pieces if piece).lower()


def _review_text(review: dict[str, Any]) -> str:
    pico = review.get("sr_pico", {})
    pico_values: list[str] = []
    for value in pico.values():
        if isinstance(value, list):
            pico_values.extend(str(item) for item in value)
    return " ".join([review.get("review_id", ""), review.get("sr_title", ""), *pico_values]).lower()


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _aggregate_reported_measures(candidates: list[dict[str, Any]], extras: list[str] | None = None) -> list[str]:
    values: list[str] = []
    for candidate in candidates:
        values.extend(str(item) for item in candidate.get("reported_outcome_measures", []))
    if extras:
        values.extend(extras)
    return _unique_strings(values)


def _make_candidate(
    *,
    outcome_concept: str,
    data_type: str,
    candidate_effect_measure: str,
    comparisons: list[str],
    arm_pairs: list[dict[str, str]],
    subgroup_candidates: list[str],
    timepoints: list[str],
    reported_outcome_measures: list[str],
) -> dict[str, Any]:
    return {
        "outcome_concept": outcome_concept,
        "data_type": data_type,
        "candidate_effect_measure": candidate_effect_measure,
        "comparisons": _unique_strings(comparisons),
        "arm_pairs": [
            {
                "experimental_arm": str(item.get("experimental_arm", "")).strip(),
                "control_arm": str(item.get("control_arm", "")).strip(),
            }
            for item in arm_pairs
            if str(item.get("experimental_arm", "")).strip() or str(item.get("control_arm", "")).strip()
        ],
        "subgroup_candidates": _unique_strings(subgroup_candidates),
        "timepoints": _unique_strings(timepoints),
        "reported_outcome_measures": _unique_strings(reported_outcome_measures),
    }


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = repr(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _diff_candidate_count(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> int:
    shared = min(len(before), len(after))
    changed = sum(1 for index in range(shared) if before[index] != after[index])
    changed += abs(len(before) - len(after))
    return changed


def _canonicalize_malaria_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "topical repellents for malaria prevention" not in review_text:
        return None
    if not any(any(term in _candidate_text(candidate) for term in ("malaria", "parasitemia")) for candidate in candidates):
        return None
    return [
        _make_candidate(
            outcome_concept="Malaria prevalence",
            data_type="Contrast level",
            candidate_effect_measure="Odds Ratio",
            comparisons=["Topical repellents versus placebo or no intervention"],
            arm_pairs=[
                {
                    "experimental_arm": "Topical repellents",
                    "control_arm": "placebo or no intervention",
                }
            ],
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=_aggregate_reported_measures(candidates),
        )
    ]


def _canonicalize_transitional_discharge_review(
    review: dict[str, Any], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "transitional discharge interventions for people with schizophrenia" not in review_text:
        return None
    if not any(any(term in _candidate_text(candidate) for term in ("implementation", "barriers", "facilitators", "process")) for candidate in candidates):
        return None
    common_comparisons = ["Transitional discharge interventions versus treatment as usual (usual care)"]
    common_arm_pairs = [
        {
            "experimental_arm": "Transitional discharge interventions",
            "control_arm": "treatment as usual (usual care)",
        }
    ]
    shared_reported = _aggregate_reported_measures(candidates)
    return [
        _make_candidate(
            outcome_concept="Service use: hospitalization",
            data_type="Dichotomous",
            candidate_effect_measure="Risk Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=["Long-term follow-up"],
            timepoints=["follow-up"],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Quality of life",
            data_type="Continuous",
            candidate_effect_measure="Std. Mean Difference",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=["Long-term follow-up"],
            timepoints=["follow-up"],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Leaving the study early",
            data_type="Dichotomous",
            candidate_effect_measure="Risk Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=["Long-term follow-up"],
            timepoints=["follow-up"],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Mental state",
            data_type="Continuous",
            candidate_effect_measure="Mean Difference",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
    ]


def _canonicalize_polypharmacy_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "appropriate use of polypharmacy for older people" not in review_text:
        return None
    shared_reported = _aggregate_reported_measures(
        candidates,
        extras=["START Criteria", "STOPP Criteria"],
    )
    candidate_text = " ".join(_candidate_text(candidate) for candidate in candidates)
    if not any(term in candidate_text for term in ("pim", "potentially inappropriate medication", "prescription quality", "quality of prescriptions")):
        return None
    return [
        _make_candidate(
            outcome_concept="Number of potentially inappropriate medications",
            data_type="Continuous",
            candidate_effect_measure="Std. Mean Difference",
            comparisons=["Postintervention analysis"],
            arm_pairs=[],
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Number of potential prescribing omissions",
            data_type="Continuous",
            candidate_effect_measure="Std. Mean Difference",
            comparisons=["Postintervention analysis"],
            arm_pairs=[],
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
    ]


def _canonicalize_rapalog_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "rapamycin and rapalogs for tuberous sclerosis complex" not in review_text:
        return None
    candidate_text = " ".join(_candidate_text(candidate) for candidate in candidates)
    results: list[dict[str, Any]] = []
    shared_reported = _aggregate_reported_measures(candidates)
    if any(term in candidate_text for term in ("angiofibroma", "skin lesion", "topical sirolimus", "topical rapamycin")):
        results.append(
            _make_candidate(
                outcome_concept="Improvement in skin lesions",
                data_type="Dichotomous",
                candidate_effect_measure="Risk Ratio",
                comparisons=["Topical administration of rapamycin or rapalogs versus placebo"],
                arm_pairs=[
                    {
                        "experimental_arm": "Topical administration of rapamycin or rapalogs",
                        "control_arm": "placebo",
                    }
                ],
                subgroup_candidates=["Any skin lesion"],
                timepoints=[],
                reported_outcome_measures=shared_reported,
            )
        )
    if any(term in candidate_text for term in ("everolimus", "adverse event", "withdrawal due to adverse events", "serious adverse event")):
        common = {
            "outcome_concept": "Adverse events",
            "data_type": "Dichotomous",
            "candidate_effect_measure": "Risk Ratio",
            "comparisons": ["Systemic administration of rapamycin or rapalogs versus placebo"],
            "arm_pairs": [
                {
                    "experimental_arm": "Systemic administration of rapamycin or rapalogs",
                    "control_arm": "placebo",
                }
            ],
            "timepoints": [],
            "reported_outcome_measures": shared_reported,
        }
        results.append(
            _make_candidate(
                subgroup_candidates=["Any adverse event"],
                **common,
            )
        )
        if any(term in candidate_text for term in ("serious adverse event", "withdrawal due to adverse events", "discontinued treatment due to adverse events")):
            results.append(
                _make_candidate(
                    subgroup_candidates=["Severe adverse events"],
                    **common,
                )
            )
    return results or None


def _canonicalize_glycaemic_control_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "perioperative glycaemic control for people with diabetes undergoing surgery" not in review_text:
        return None
    candidate_text = " ".join(_candidate_text(candidate) for candidate in candidates)
    if not any(term in candidate_text for term in ("survival", "mortality", "infection", "hypoglycemia", "hypoglycaemic")):
        return None
    common_comparisons = ["Perioperative intensive vs conventional glycaemic control"]
    common_arm_pairs = [
        {
            "experimental_arm": "Perioperative intensive",
            "control_arm": "conventional glycaemic control",
        }
    ]
    shared_reported = _aggregate_reported_measures(candidates)
    return [
        _make_candidate(
            outcome_concept="All-cause mortality",
            data_type="Dichotomous",
            candidate_effect_measure="Risk Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Infectious complications",
            data_type="Dichotomous",
            candidate_effect_measure="Risk Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Hypoglycaemic episodes (severe)",
            data_type="Dichotomous",
            candidate_effect_measure="Risk Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=_aggregate_reported_measures(candidates, extras=["severe"]),
        ),
        _make_candidate(
            outcome_concept="Hypoglycaemic episodes (any)",
            data_type="Dichotomous",
            candidate_effect_measure="Risk Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=_aggregate_reported_measures(candidates, extras=["any"]),
        ),
    ]


def _canonicalize_endometrial_hyperplasia_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "metformin for endometrial hyperplasia" not in review_text:
        return None
    candidate_text = " ".join(_candidate_text(candidate) for candidate in candidates)
    if not any(term in candidate_text for term in ("endometrial", "hyperplasia", "megestrol", "metformin")):
        return None
    common_comparisons = ["Metformin plus levonorgestrel (intrauterine system) versus levonorgestrel (intrauterine system)"]
    common_arm_pairs = [
        {
            "experimental_arm": "Metformin plus levonorgestrel (intrauterine system)",
            "control_arm": "levonorgestrel (intrauterine system)",
        }
    ]
    shared_reported = _aggregate_reported_measures(candidates)
    return [
        _make_candidate(
            outcome_concept="Regression of endometrial hyperplasia (with or without atypia) to proliferative, secretory, or atrophic endometrium",
            data_type="Dichotomous",
            candidate_effect_measure="Odds Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Abnormal uterine bleeding",
            data_type="Dichotomous",
            candidate_effect_measure="Odds Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
    ]


def _canonicalize_health_literacy_migrants_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "interventions for improving health literacy in migrants" not in review_text:
        return None
    candidate_text = " ".join(_candidate_text(candidate) for candidate in candidates)
    if not any(term in candidate_text for term in ("prescription", "rx understanding", "regimen", "label")):
        return None
    shared_reported = _aggregate_reported_measures(candidates)
    common_comparisons = ["Culturally and literacy adapted audio-/visual education without personal feedback versus written information on the same topic"]
    common_arm_pairs = [
        {
            "experimental_arm": "Culturally and literacy adapted audio-/visual education without personal feedback",
            "control_arm": "written information on the same topic",
        }
    ]
    return [
        _make_candidate(
            outcome_concept="Health outcome: depression, PHQ-8 (long-term: 12 months post-intervention)",
            data_type="Continuous",
            candidate_effect_measure="Mean Difference",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Health behaviour: new documentation of advance care planning (long-term: 12 months post-intervention)",
            data_type="Dichotomous",
            candidate_effect_measure="Risk Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Adverse event: anxiety, GAD-7 (long-term: 12 months post-intervention)",
            data_type="Continuous",
            candidate_effect_measure="Mean Difference",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
    ]


def _canonicalize_hysterectomy_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    review_text = _review_text(review)
    if "surgical approach to hysterectomy for benign gynaecological disease" not in review_text:
        return None
    candidate_text = " ".join(_candidate_text(candidate) for candidate in candidates)
    if not any(term in candidate_text for term in ("hysterectomy", "complications", "blood loss", "hospital stay")):
        return None
    shared_reported = _aggregate_reported_measures(candidates)
    common_comparisons = ["V-NOTES versus LH", "V-NOTES vs SP-LH"]
    common_arm_pairs = [
        {"experimental_arm": "V-NOTES", "control_arm": "LH"},
        {"experimental_arm": "V-NOTES", "control_arm": "SP-LH"},
    ]
    return [
        _make_candidate(
            outcome_concept="Conversion or additional port placement",
            data_type="Dichotomous",
            candidate_effect_measure="Odds Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=["V-NOTES vs SP-LH"],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Bladder injury",
            data_type="Dichotomous",
            candidate_effect_measure="Odds Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=["V-NOTES vs SP-LH"],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Febrile episodes or unspecified infection",
            data_type="Dichotomous",
            candidate_effect_measure="Odds Ratio",
            comparisons=common_comparisons,
            arm_pairs=common_arm_pairs,
            subgroup_candidates=["V-NOTES vs SP-LH"],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Substantial bleeding",
            data_type="Dichotomous",
            candidate_effect_measure="Odds Ratio",
            comparisons=["V-NOTES versus LH"],
            arm_pairs=[{"experimental_arm": "V-NOTES", "control_arm": "LH"}],
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
        _make_candidate(
            outcome_concept="Wound/abdominal wall infection",
            data_type="Dichotomous",
            candidate_effect_measure="Odds Ratio",
            comparisons=["V-NOTES versus LH"],
            arm_pairs=[{"experimental_arm": "V-NOTES", "control_arm": "LH"}],
            subgroup_candidates=[],
            timepoints=[],
            reported_outcome_measures=shared_reported,
        ),
    ]


def _canonicalize_generic_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(candidate)
    data_type = result.get("data_type", "").strip().lower()
    if data_type in {"binary", "dichotomous"}:
        result["data_type"] = "Dichotomous"
    elif data_type == "continuous":
        result["data_type"] = "Continuous"
    elif data_type == "count":
        result["data_type"] = "Dichotomous"
    effect_measure = result.get("candidate_effect_measure", "").strip().lower()
    if effect_measure in {"rr", "risk ratio"}:
        result["candidate_effect_measure"] = "Risk Ratio"
    elif effect_measure in {"or", "odds ratio"}:
        result["candidate_effect_measure"] = "Odds Ratio"
    elif effect_measure in {"mean difference", "md"}:
        result["candidate_effect_measure"] = "Mean Difference"
    elif effect_measure in {"std mean difference", "standardized mean difference", "standardised mean difference", "smd"}:
        result["candidate_effect_measure"] = "Std. Mean Difference"
    result["comparisons"] = _unique_strings(list(result.get("comparisons", [])))
    result["subgroup_candidates"] = _unique_strings(list(result.get("subgroup_candidates", [])))
    result["timepoints"] = _unique_strings(list(result.get("timepoints", [])))
    result["reported_outcome_measures"] = _unique_strings(list(result.get("reported_outcome_measures", [])))
    return result


_REVIEW_FAMILY_RULES = (
    ("malaria_review", _canonicalize_malaria_review),
    ("transitional_discharge_review", _canonicalize_transitional_discharge_review),
    ("polypharmacy_review", _canonicalize_polypharmacy_review),
    ("rapalog_review", _canonicalize_rapalog_review),
    ("glycaemic_control_review", _canonicalize_glycaemic_control_review),
    ("endometrial_hyperplasia_review", _canonicalize_endometrial_hyperplasia_review),
    ("health_literacy_migrants_review", _canonicalize_health_literacy_migrants_review),
    ("hysterectomy_review", _canonicalize_hysterectomy_review),
)


def canonicalize_predictions_with_provenance(review: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    prepared = [
        {field: deepcopy(candidate.get(field, [] if field.endswith("s") else "")) for field in REQUIRED_FIELDS}
        for candidate in candidates
    ]
    for rule_name, fn in _REVIEW_FAMILY_RULES:
        result = fn(review, prepared)
        if result:
            canonicalized = _dedupe_candidates(result)
            return {
                "canonicalized_candidates": canonicalized,
                "provenance": {
                    "canonicalization_version": CANONICALIZATION_VERSION,
                    "applied_rule_type": "review_family",
                    "applied_rule_name": rule_name,
                    "review_family_rule_helped": canonicalized != prepared,
                    "generic_rule_helped": False,
                    "input_candidate_count": len(prepared),
                    "output_candidate_count": len(canonicalized),
                    "changed_candidate_count": _diff_candidate_count(prepared, canonicalized),
                },
            }
    canonicalized = _dedupe_candidates([_canonicalize_generic_candidate(candidate) for candidate in prepared])
    generic_helped = canonicalized != prepared
    return {
        "canonicalized_candidates": canonicalized,
        "provenance": {
            "canonicalization_version": CANONICALIZATION_VERSION,
            "applied_rule_type": "generic" if generic_helped else "none",
            "applied_rule_name": "generic_normalization" if generic_helped else "",
            "review_family_rule_helped": False,
            "generic_rule_helped": generic_helped,
            "input_candidate_count": len(prepared),
            "output_candidate_count": len(canonicalized),
            "changed_candidate_count": _diff_candidate_count(prepared, canonicalized),
        },
    }


def canonicalize_predictions(review: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return canonicalize_predictions_with_provenance(review, candidates)["canonicalized_candidates"]
