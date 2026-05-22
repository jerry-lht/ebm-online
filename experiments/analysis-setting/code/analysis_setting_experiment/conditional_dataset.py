from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .conditional_constants import (
    CONDITIONAL_DATASET_VERSION,
    CONDITIONAL_EVIDENCE_MODES,
    CONDITIONAL_SPLIT_VERSION,
    MAX_FULL_TEXT_CHARS_PER_STUDY,
)
from .conditional_comparison_candidates import build_comparison_candidates
from .conditional_normalization import (
    arm_pair_key,
    clean_text,
    dedupe_arm_pairs,
    dedupe_preserve_order,
    normalize_text,
    normalize_string_list,
    slugify,
    stable_digest,
)
from .dataset import abstract_study_count_bucket, build_review_record, gold_candidate_count_bucket, make_dev_test_split
from .io_utils import dump_json, dump_jsonl, load_jsonl

_PRIORITY_SECTION_HINTS = (
    "title",
    "abstract",
    "summary",
    "method",
    "result",
)


def _review_metadata(review: dict[str, Any]) -> dict[str, Any]:
    included_studies = review.get("included_studies", [])
    abstract_count = sum(1 for study in included_studies if clean_text(study.get("abstract")))
    gold_candidates = list(review.get("gold_partial_analysis_settings", []))
    coverage_level = review.get("evidence_coverage", {}).get("coverage_level", "")
    return {
        "review_id": review["review_id"],
        "abstract_study_count": abstract_count,
        "abstract_study_count_bucket": abstract_study_count_bucket(abstract_count),
        "gold_candidate_count": len(gold_candidates),
        "gold_candidate_count_bucket": gold_candidate_count_bucket(len(gold_candidates)),
        "coverage_level": coverage_level,
    }



def _format_study_header(study: dict[str, Any]) -> str:
    title = clean_text(study.get("primary_report", {}).get("title"))
    study_id = clean_text(study.get("study_id"))
    study_year = clean_text(study.get("study_year"))
    tier = clean_text(study.get("evidence_tier"))
    return f"Study ID: {study_id}\nStudy Year: {study_year}\nTitle: {title}\nEvidence Tier: {tier}"



def _sorted_sections(study: dict[str, Any]) -> list[dict[str, str]]:
    sections = study.get("full_content", {}).get("sections", [])
    prioritized: list[tuple[int, int, dict[str, str]]] = []
    for index, section in enumerate(sections):
        name = clean_text(section.get("section")).lower()
        priority = 10
        for rank, hint in enumerate(_PRIORITY_SECTION_HINTS):
            if hint in name:
                priority = rank
                break
        prioritized.append((priority, index, section))
    prioritized.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in prioritized]



def _build_full_text_body(sections: list[dict[str, str]], *, char_budget: int = MAX_FULL_TEXT_CHARS_PER_STUDY) -> str:
    pieces: list[str] = []
    used = 0
    for section in sections:
        section_name = clean_text(section.get("section")) or "Section"
        text = clean_text(section.get("text"))
        if not text:
            continue
        chunk = f"{section_name}\n{text}"
        if used >= char_budget:
            break
        remaining = char_budget - used
        if len(chunk) > remaining:
            chunk = chunk[:remaining].rstrip()
        if not chunk:
            continue
        pieces.append(chunk)
        used += len(chunk) + 2
    return "\n\n".join(pieces).strip()



def build_study_evidence(study: dict[str, Any], *, evidence_mode: str) -> dict[str, Any] | None:
    if evidence_mode not in CONDITIONAL_EVIDENCE_MODES:
        raise ValueError(f"unknown_evidence_mode:{evidence_mode}")
    source = "abstract"
    abstract = clean_text(study.get("abstract"))
    sections = [
        {
            "section": clean_text(section.get("section")) or "Section",
            "text": clean_text(section.get("text")),
        }
        for section in _sorted_sections(study)
        if clean_text(section.get("text"))
    ]
    full_text = _build_full_text_body(sections)
    if evidence_mode == "abstract-only":
        body = abstract
    else:
        if full_text:
            body = full_text
            source = "full_text"
        else:
            body = abstract
    if not body:
        return None
    return {
        "study_id": clean_text(study.get("study_id")),
        "study_year": clean_text(study.get("study_year")),
        "primary_report_title": clean_text(study.get("primary_report", {}).get("title")),
        "evidence_tier": clean_text(study.get("evidence_tier")),
        "evidence_source": source,
        "has_tables": bool(study.get("full_content", {}).get("tables")),
        "text": f"{_format_study_header(study)}\n\n{body}".strip(),
        "abstract_text": abstract,
        "full_text_sections": sections,
    }



def build_review_evidence(review: dict[str, Any], *, evidence_mode: str) -> list[dict[str, Any]]:
    evidence_rows: list[dict[str, Any]] = []
    for study in review.get("included_studies", []):
        built = build_study_evidence(study, evidence_mode=evidence_mode)
        if built is not None:
            evidence_rows.append(built)
    return evidence_rows



def _candidate_groups_by_outcome(review: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in review.get("gold_partial_analysis_settings", []):
        outcome = clean_text(candidate.get("outcome_concept"))
        if not outcome:
            continue
        grouped[outcome].append(candidate)
    return grouped



def _comparison_groups(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        seen_local: set[str] = set()
        for comparison in candidate.get("comparisons", []):
            raw = clean_text(comparison)
            normalized = normalize_text(raw)
            if not normalized or normalized in seen_local:
                continue
            seen_local.add(normalized)
            grouped[raw].append(candidate)
    return grouped



def _candidate_data_types(candidates: list[dict[str, Any]]) -> list[str]:
    return dedupe_preserve_order([clean_text(candidate.get("data_type")) for candidate in candidates])



def _candidate_effect_measures(candidates: list[dict[str, Any]]) -> list[str]:
    return dedupe_preserve_order([clean_text(candidate.get("candidate_effect_measure")) for candidate in candidates])



def _instance_id(review_id: str, task_name: str, parts: list[str]) -> str:
    slug_parts = [slugify(part, fallback="x") for part in parts if clean_text(part)]
    prefix = "__".join([review_id.lower(), task_name] + slug_parts[:3])
    digest = stable_digest([review_id, task_name, *parts])
    return f"{prefix}__{digest}"



def _base_instance(
    review: dict[str, Any],
    *,
    task_name: str,
    outcome_concept: str,
    evidence_mode: str,
    study_evidence: list[dict[str, Any]],
    task_metadata: dict[str, Any],
    gold_target: dict[str, Any],
    instance_parts: list[str],
) -> dict[str, Any]:
    return {
        "task_name": task_name,
        "instance_id": _instance_id(review["review_id"], task_name, instance_parts),
        "review_id": review["review_id"],
        "sr_title": clean_text(review.get("sr_title")),
        "sr_pico": review.get("sr_pico", {}),
        "outcome_concept": outcome_concept,
        "evidence_mode": evidence_mode,
        "study_evidence": study_evidence,
        "gold_target": gold_target,
        "task_metadata": task_metadata,
        "metadata": {
            **_review_metadata(review),
            "dataset_version": CONDITIONAL_DATASET_VERSION,
            "split_version": CONDITIONAL_SPLIT_VERSION,
        },
    }



def expand_review_to_instances(review: dict[str, Any], *, evidence_mode: str) -> list[dict[str, Any]]:
    evidence = build_review_evidence(review, evidence_mode=evidence_mode)
    instances: list[dict[str, Any]] = []
    for outcome_concept, candidates in _candidate_groups_by_outcome(review).items():
        normalized_comparisons = normalize_string_list(
            [comparison for candidate in candidates for comparison in candidate.get("comparisons", [])]
        )
        comparison_groups = _comparison_groups(candidates)
        for data_type in _candidate_data_types(candidates):
            matching = [candidate for candidate in candidates if clean_text(candidate.get("data_type")) == data_type]
            data_type_instance_id = _instance_id(review["review_id"], "data_type", [outcome_concept, data_type])
            instances.append(
                _base_instance(
                    review,
                    task_name="data_type",
                    outcome_concept=outcome_concept,
                    evidence_mode=evidence_mode,
                    study_evidence=evidence,
                    task_metadata={
                        "candidate_ids": [candidate.get("candidate_id", "") for candidate in matching],
                    },
                    gold_target={"data_type": data_type},
                    instance_parts=[outcome_concept, data_type],
                )
            )
            for effect_measure in _candidate_effect_measures(matching):
                effect_matching = [
                    candidate
                    for candidate in matching
                    if clean_text(candidate.get("candidate_effect_measure")) == effect_measure
                ]
                instances.append(
                    _base_instance(
                        review,
                        task_name="candidate_effect_measure",
                        outcome_concept=outcome_concept,
                        evidence_mode=evidence_mode,
                        study_evidence=evidence,
                        task_metadata={
                            "condition_data_type": data_type,
                            "linked_data_type_instance_id": data_type_instance_id,
                            "candidate_ids": [candidate.get("candidate_id", "") for candidate in effect_matching],
                        },
                        gold_target={"candidate_effect_measure": effect_measure},
                        instance_parts=[outcome_concept, data_type, effect_measure],
                    )
                )
        comparison_instance = _base_instance(
            review,
            task_name="comparisons",
            outcome_concept=outcome_concept,
            evidence_mode=evidence_mode,
            study_evidence=evidence,
            task_metadata={
                "comparison_count": len(normalized_comparisons),
            },
            gold_target={"comparisons": normalized_comparisons},
            instance_parts=[outcome_concept, "comparisons"],
        )
        comparison_instance["task_metadata"]["comparison_candidates"] = build_comparison_candidates(comparison_instance)
        instances.append(comparison_instance)
        for comparison_raw, comparison_candidates in comparison_groups.items():
            arm_pairs = dedupe_arm_pairs(
                [pair for candidate in comparison_candidates for pair in candidate.get("arm_pairs", [])]
            )
            parseable_from_comparison = " versus " in normalize_text(comparison_raw) or " vs " in normalize_text(comparison_raw)
            instances.append(
                _base_instance(
                    review,
                    task_name="arm_pairs",
                    outcome_concept=outcome_concept,
                    evidence_mode=evidence_mode,
                    study_evidence=evidence,
                    task_metadata={
                        "comparison": comparison_raw,
                        "parseable_from_comparison": parseable_from_comparison,
                        "requires_evidence_grounding": not parseable_from_comparison,
                        "candidate_ids": [candidate.get("candidate_id", "") for candidate in comparison_candidates],
                    },
                    gold_target={"arm_pairs": arm_pairs},
                    instance_parts=[outcome_concept, comparison_raw],
                )
            )
        structured_items: list[dict[str, Any]] = []
        for comparison_raw in sorted(comparison_groups, key=normalize_text):
            comparison_candidates = comparison_groups[comparison_raw]
            structured_items.append(
                {
                    "comparison": comparison_raw,
                    "arm_pairs": dedupe_arm_pairs(
                        [pair for candidate in comparison_candidates for pair in candidate.get("arm_pairs", [])]
                    ),
                }
            )
        instances.append(
            _base_instance(
                review,
                task_name="comparisons_and_arm_pairs",
                outcome_concept=outcome_concept,
                evidence_mode=evidence_mode,
                study_evidence=evidence,
                task_metadata={
                    "comparison_count": len(structured_items),
                },
                gold_target={"items": structured_items},
                instance_parts=[outcome_concept, "comparisons_and_arm_pairs"],
            )
        )
    instances.sort(key=lambda item: (item["task_name"], item["instance_id"]))
    return instances



def load_benchmark_reviews(benchmark_path: Path) -> list[dict[str, Any]]:
    return load_jsonl(benchmark_path)



def _split_reviews(reviews: list[dict[str, Any]], *, dev_ratio: float, seed: int) -> dict[str, list[dict[str, Any]]]:
    split_records = [build_review_record(review) for review in reviews]
    record_by_review_id = {record["review_id"]: record for record in split_records}
    split_rows = make_dev_test_split(list(record_by_review_id.values()), dev_ratio=dev_ratio, seed=seed)
    reviews_by_id = {review["review_id"]: review for review in reviews}
    return {
        split_name: [reviews_by_id[row["review_id"]] for row in rows]
        for split_name, rows in split_rows.items()
    }



def export_conditional_dataset(
    benchmark_path: Path,
    output_dir: Path,
    *,
    dev_ratio: float,
    seed: int,
    evidence_mode: str,
) -> dict[str, Any]:
    reviews = load_benchmark_reviews(benchmark_path)
    split_reviews = _split_reviews(reviews, dev_ratio=dev_ratio, seed=seed)
    split_counts: dict[str, int] = {}
    review_counts: dict[str, int] = {}
    task_counts: dict[str, dict[str, int]] = {}
    for split_name, split_rows in split_reviews.items():
        instances: list[dict[str, Any]] = []
        per_task = defaultdict(int)
        for review in split_rows:
            expanded = expand_review_to_instances(review, evidence_mode=evidence_mode)
            instances.extend(expanded)
            for item in expanded:
                per_task[item["task_name"]] += 1
        instances.sort(key=lambda item: item["instance_id"])
        dump_jsonl(output_dir / "conditional_splits" / evidence_mode / f"{split_name}.jsonl", instances)
        split_counts[split_name] = len(instances)
        review_counts[split_name] = len(split_rows)
        task_counts[split_name] = dict(sorted(per_task.items()))
    summary = {
        "dataset_version": CONDITIONAL_DATASET_VERSION,
        "split_version": CONDITIONAL_SPLIT_VERSION,
        "evidence_mode": evidence_mode,
        "seed": seed,
        "dev_ratio": dev_ratio,
        "review_count": len(reviews),
        "split_review_counts": review_counts,
        "split_instance_counts": split_counts,
        "task_counts": task_counts,
    }
    dump_json(output_dir / "conditional_splits" / evidence_mode / "metadata.json", summary)
    return summary



def arm_pairs_match_comparison(pair: dict[str, Any], comparison: str) -> bool:
    normalized_comparison = normalize_text(comparison)
    left, right = arm_pair_key(pair)
    return bool(left and right and left in normalized_comparison and right in normalized_comparison)
