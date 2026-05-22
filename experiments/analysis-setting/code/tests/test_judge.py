from __future__ import annotations

import json

from analysis_setting_experiment.judge import (
    JsonFileJudgeBackend,
    RunConfig,
    aggregate_judge_results,
    build_judge_pairs,
    build_judge_prompt,
    build_rigid_review_result,
    judge_pair,
    parse_judge_response,
    summarize_judge_review,
)


def _candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "outcome_concept": "smoking cessation",
        "data_type": "Dichotomous",
        "candidate_effect_measure": "Odds Ratio",
        "comparisons": ["drug versus placebo"],
        "arm_pairs": [{"experimental_arm": "drug", "control_arm": "placebo"}],
        "subgroup_candidates": [],
        "timepoints": [],
        "reported_outcome_measures": [],
    }
    candidate.update(overrides)
    return candidate


def _review_row() -> dict[str, object]:
    return {
        "review_id": "R1",
        "sr_title": "Smoking review",
        "sr_pico": {"intervention": ["drug"], "comparison": ["placebo"]},
        "metadata": {"coverage_level": "HIGH"},
        "gold_partial_analysis_settings": [_candidate()],
    }


def test_parse_judge_response_accepts_valid_schema() -> None:
    payload = parse_judge_response(
        json.dumps(
            {
                "verdict": "partially_equivalent",
                "reason_tags": ["comparison_level_mismatch"],
                "confidence": "high",
                "rationale": "Same core setting but one side is slightly more specific.",
            }
        )
    )
    assert payload["verdict"] == "partially_equivalent"
    assert payload["reason_tags"] == ["comparison_level_mismatch"]


def test_build_judge_prompt_mentions_semantic_instruction() -> None:
    prompt = build_judge_prompt(_review_row(), _candidate(), _candidate())
    assert "same review-level analysis setting" in prompt
    assert "partially_equivalent" in prompt


def test_judge_review_summary_counts_strict_and_loose_matches() -> None:
    review_row = _review_row()
    prediction_payload = {
        "schema_valid": True,
        "parse_status": "success",
        "raw_parsed_prediction_json": [_candidate()],
        "canonicalized_prediction_json": [_candidate(comparisons=["drug vs placebo"])],
        "canonicalization_provenance": {"applied_rule_type": "generic"},
    }
    rigid = build_rigid_review_result(
        review_row,
        prediction_payload,
        split="dev",
        threshold=0.65,
        prediction_mode="canonicalized",
    )
    pairs = build_judge_pairs(rigid)
    backend = JsonFileJudgeBackend(
        {
            "R1::pred0::gold0": {
                "verdict": "partially_equivalent",
                "reason_tags": ["comparison_level_mismatch"],
                "confidence": "high",
                "rationale": "Same setting with light comparison wording drift.",
            }
        }
    )
    config = RunConfig(model_name="judge", model_version="v1", split="dev", output_dir=None)  # type: ignore[arg-type]
    pair_results = [judge_pair(backend, config, review_row, pair) for pair in pairs]
    summary = summarize_judge_review(rigid, pair_results)
    assert summary["semantic_strict_match_count"] == 1
    assert summary["semantic_loose_match_count"] == 1
    aggregate = aggregate_judge_results([summary])
    assert aggregate["semantic_candidate_f1"] == 1.0


def test_build_rigid_review_result_uses_raw_fallback_for_legacy_artifact() -> None:
    review_row = _review_row()
    prediction_payload = {
        "schema_valid": True,
        "parse_status": "success",
        "parsed_prediction_json": [_candidate()],
    }
    result = build_rigid_review_result(
        review_row,
        prediction_payload,
        split="dev",
        threshold=0.65,
        prediction_mode="raw",
    )
    assert result["raw_prediction_fallback_used"] is True
    assert result["matched_pair_count"] == 1


def test_judge_cli_parser_supports_concurrency() -> None:
    from analysis_setting_experiment.cli import build_parser

    parser = build_parser()
    args = parser.parse_args([
        "judge-evaluate",
        "--dataset-path", "dev.jsonl",
        "--output-dir", "out",
        "--model-name", "demo",
        "--split", "dev",
        "--concurrency", "4",
    ])
    assert args.concurrency == 4
