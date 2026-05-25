"""Dataset preparation for benchmark2-v2 item evaluation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .constants import DEFAULT_DEV_FRACTION, DEFAULT_EVIDENCE_MODE, DEFAULT_SPLIT_SEED, DIRECT_FIELDS_BY_DATA_TYPE
from .io_utils import ensure_dir, write_json, write_jsonl
from .normalize import normalize_subgroup, normalize_timepoints, stable_hash

CONTRAST_LEVEL_NON_DIRECT_ROLES = {"conditionally_extractable"}
CONTRAST_LEVEL_ALLOWED_FIELDS = set(DIRECT_FIELDS_BY_DATA_TYPE["Contrast level"])


def assign_split(review_id: str, *, dev_fraction: float, seed: str) -> str:
    bucket = int(stable_hash(f"{seed}::{review_id}")[:8], 16) / 0xFFFFFFFF
    return "dev" if bucket < dev_fraction else "test"


def _study_payload(sample: dict, *, evidence_mode: str) -> dict:
    return {
        "sample_id": sample["sample_id"],
        "review_id": sample["review_id"],
        "study_id": sample["study_id"],
        "study_year": sample.get("study_year"),
        "primary_report": sample.get("primary_report") or {},
        "sr_title": sample.get("sr_title"),
        "sr_pico": sample.get("sr_pico") or {},
        "full_content": sample.get("full_content") or {},
        "evidence_mode": evidence_mode,
    }


def _setting_context(candidate: dict) -> dict:
    return {
        "candidate_id": candidate["candidate_id"],
        "analysis_label": candidate.get("analysis_label"),
        "outcome_concept": candidate.get("outcome_concept"),
        "comparison": (candidate.get("comparisons") or [None])[0],
        "comparisons": candidate.get("comparisons") or [],
        "data_type": candidate.get("data_type"),
        "effect_measure": candidate.get("candidate_effect_measure"),
        "arm_pairs": candidate.get("arm_pairs") or [],
        "subgroup_candidates": candidate.get("subgroup_candidates") or [],
        "timepoints": candidate.get("timepoints") or [],
        "reported_outcome_measures": candidate.get("reported_outcome_measures") or [],
    }


def _normalize_gold_direct_fields(row: dict) -> list[dict]:
    data_type = row.get("data_type")
    direct_fields = list(row.get("direct_extraction_fields") or [])
    if data_type != "Contrast level":
        return direct_fields
    seen = {field.get("field") for field in direct_fields if field.get("field")}
    for field in row.get("non_direct_fields") or []:
        field_name = field.get("field")
        if field.get("role") not in CONTRAST_LEVEL_NON_DIRECT_ROLES:
            continue
        if field_name not in CONTRAST_LEVEL_ALLOWED_FIELDS or field_name in seen:
            continue
        direct_fields.append({"field": field_name, "value": field.get("value")})
        seen.add(field_name)
    return direct_fields


def _item_payload(item: dict) -> dict:
    return {
        "item_id": item["item_id"],
        "match_status": item.get("match_status"),
        "comparison": item.get("comparison"),
        "subgroup": item.get("subgroup"),
        "timepoints": item.get("timepoints") or [],
        "gold_extraction_rows": item.get("gold_extraction_rows") or [],
    }


def _support_status(subgroup: object, timepoints: list[object]) -> dict:
    return {
        "subgroup_support_status": "supported" if normalize_subgroup(subgroup) is not None else "not_supported",
        "timepoint_support_status": "supported" if normalize_timepoints(timepoints) else "not_supported",
    }


def _gold_items_by_setting(candidate: dict) -> list[dict]:
    return [_item_payload(item) for item in candidate.get("analysis_items") or []]


def prepare_instances(
    *,
    dataset_path: str | Path,
    output_dir: str | Path,
    dev_fraction: float = DEFAULT_DEV_FRACTION,
    split_seed: str = DEFAULT_SPLIT_SEED,
    max_samples: int | None = None,
    max_settings: int | None = None,
    target_split: str | None = None,
    evidence_mode: str = DEFAULT_EVIDENCE_MODE,
) -> dict:
    output_root = ensure_dir(output_dir)
    support_instances = []
    proposal_instances = []
    oracle_instances = []
    routed_instances = []
    review_manifest = {}
    setting_counter = 0

    with Path(dataset_path).open("r", encoding="utf-8") as handle:
        for sample_index, line in enumerate(handle):
            if max_samples is not None and sample_index >= max_samples:
                break
            sample = __import__("json").loads(line)
            split = assign_split(sample["review_id"], dev_fraction=dev_fraction, seed=split_seed)
            review_manifest.setdefault(sample["review_id"], {"review_id": sample["review_id"], "split": split})
            study = _study_payload(sample, evidence_mode=evidence_mode)
            for candidate in sample.get("gold_partial_analysis_settings") or []:
                if target_split is not None and split != target_split:
                    continue
                if max_settings is not None and setting_counter >= max_settings:
                    break
                setting = _setting_context(candidate)
                gold_items = _gold_items_by_setting(candidate)
                base_instance_id = f"{sample['sample_id']}::{candidate['candidate_id']}"
                proposal_instances.append(
                    {
                        "instance_id": base_instance_id,
                        "instance_type": "proposal",
                        "split": split,
                        "study": study,
                        "setting_context": setting,
                        "gold_items": [
                            {
                                "subgroup": item.get("subgroup"),
                                "timepoints": item.get("timepoints") or [],
                            }
                            for item in gold_items
                        ],
                    }
                )
                routed_instances.append(
                    {
                        "instance_id": base_instance_id,
                        "instance_type": "routed_extraction",
                        "split": split,
                        "study": study,
                        "setting_context": setting,
                        "gold_items": gold_items,
                    }
                )
                for item in gold_items:
                    support_instances.append(
                        {
                            "instance_id": f"{base_instance_id}::{item['item_id']}::support",
                            "instance_type": "support",
                            "split": split,
                            "study": study,
                            "setting_context": setting,
                            "official_item": {
                                "item_id": item["item_id"],
                                "subgroup": item.get("subgroup"),
                                "timepoints": item.get("timepoints") or [],
                                "match_status": item.get("match_status"),
                            },
                            "gold_support": _support_status(item.get("subgroup"), item.get("timepoints") or []),
                        }
                    )
                    oracle_instances.append(
                        {
                            "instance_id": f"{base_instance_id}::{item['item_id']}::oracle_extraction",
                            "instance_type": "oracle_extraction",
                            "parent_setting_instance_id": base_instance_id,
                            "split": split,
                            "study": study,
                            "setting_context": setting,
                            "official_item": {
                                "item_id": item["item_id"],
                                "comparison": item.get("comparison"),
                                "subgroup": item.get("subgroup"),
                                "timepoints": item.get("timepoints") or [],
                                "match_status": item.get("match_status"),
                            },
                            "gold_extraction_rows": [
                                {
                                    "extraction_row_id": row.get("extraction_row_id"),
                                    "row_variant_index": row.get("row_variant_index"),
                                    "data_type": row.get("data_type"),
                                    "effect_measure": row.get("effect_measure"),
                                    "direct_extraction_fields": _normalize_gold_direct_fields(row),
                                }
                                for row in item.get("gold_extraction_rows") or []
                            ],
                        }
                    )
                setting_counter += 1
            if max_settings is not None and setting_counter >= max_settings:
                break

    write_jsonl(output_root / "support_instances.jsonl", support_instances)
    write_jsonl(output_root / "proposal_instances.jsonl", proposal_instances)
    write_jsonl(output_root / "oracle_extraction_instances.jsonl", oracle_instances)
    write_jsonl(output_root / "routed_extraction_instances.jsonl", routed_instances)

    review_rows = sorted(review_manifest.values(), key=lambda row: row["review_id"])
    counts = {
        "reviews": len(review_rows),
        "dev_reviews": sum(1 for row in review_rows if row["split"] == "dev"),
        "test_reviews": sum(1 for row in review_rows if row["split"] == "test"),
        "support_instances": len(support_instances),
        "proposal_instances": len(proposal_instances),
        "oracle_extraction_instances": len(oracle_instances),
        "routed_extraction_instances": len(routed_instances),
    }
    split_manifest = {
        "split_seed": split_seed,
        "dev_fraction": dev_fraction,
        "target_split": target_split,
        "evidence_mode": evidence_mode,
        "reviews": review_rows,
        "counts": counts,
    }
    write_json(output_root / "split_manifest.json", split_manifest)
    write_json(
        output_root / "prepare_data_summary.json",
        {
            "dataset_path": str(dataset_path),
            "output_dir": str(output_root),
            "counts": counts,
            "target_split": target_split,
            "evidence_mode": evidence_mode,
            "direct_fields_by_data_type": DIRECT_FIELDS_BY_DATA_TYPE,
            "match_status_counts": dict(
                sorted(
                    Counter(
                        instance["official_item"].get("match_status", "unknown")
                        for instance in oracle_instances
                    ).items()
                )
            ),
        },
    )
    return split_manifest
