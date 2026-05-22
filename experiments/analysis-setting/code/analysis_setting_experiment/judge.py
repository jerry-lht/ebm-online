from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluator import candidate_similarity, evaluate_review
from .io_utils import load_json
from .runner import ModelBackend, OpenAIResponsesBackend, RunConfig

JUDGE_VERSION = "analysis_setting_semantic_judge_v1"
ALLOWED_VERDICTS = ("equivalent", "partially_equivalent", "not_equivalent")
ALLOWED_REASON_TAGS = (
    "outcome_level_mismatch",
    "comparison_level_mismatch",
    "effect_measure_mismatch",
    "data_type_mismatch",
    "timepoint_or_subgroup_mismatch",
    "genuinely_different_analysis_setting",
)


@dataclass(frozen=True)
class JudgePairContext:
    review_id: str
    pred_index: int
    gold_index: int
    pair_source: str
    rigid_similarity_score: float
    prediction_candidate: dict[str, Any]
    gold_candidate: dict[str, Any]


class MockJudgeBackend(ModelBackend):
    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:
        return json.dumps(
            {
                "verdict": "not_equivalent",
                "reason_tags": ["genuinely_different_analysis_setting"],
                "confidence": "medium",
                "rationale": "Mock judge backend defaulted to not_equivalent.",
            },
            ensure_ascii=False,
        )


class JsonFileJudgeBackend(ModelBackend):
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses

    def generate(self, prompt: str, review: dict[str, Any], config: RunConfig) -> str:
        pair_key = review.get("judge_pair_key", "")
        value = self.responses.get(pair_key)
        if value is None:
            raise KeyError(f"missing_judge_pair:{pair_key}")
        return json.dumps(value, ensure_ascii=False)


def build_judge_backend(kind: str, *, json_source: Path | None = None) -> ModelBackend:
    if kind == "mock":
        return MockJudgeBackend()
    if kind == "json_file":
        if json_source is None:
            raise ValueError("json_source is required for json_file backend")
        return JsonFileJudgeBackend(load_json(json_source))
    if kind == "openai":
        return OpenAIResponsesBackend()
    raise ValueError(f"unknown_judge_backend:{kind}")


def _safe_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def build_judge_prompt(
    review_context: dict[str, Any],
    prediction_candidate: dict[str, Any],
    gold_candidate: dict[str, Any],
) -> str:
    review_payload = {
        "review_title": review_context.get("sr_title", ""),
        "sr_pico": review_context.get("sr_pico", {}),
    }
    response_schema = {
        "verdict": "equivalent | partially_equivalent | not_equivalent",
        "reason_tags": list(ALLOWED_REASON_TAGS),
        "confidence": "high | medium | low",
        "rationale": "short rationale",
    }
    parts = [
        "You are judging whether two structured candidates describe the same review-level analysis setting.",
        "Judge only whether they refer to the same setting a review author would meta-analyze.",
        "Ignore minor wording differences and preserve semantic equivalence over surface form.",
        "If the prediction is slightly more specific or slightly more general but still clearly refers to the same canonical setting, use partially_equivalent.",
        "Only use not_equivalent when the outcome target, comparison target, effect target, data type, subgroup, or timepoint is materially different.",
        "Return JSON only with this schema:",
        json.dumps(response_schema, ensure_ascii=False, indent=2),
        "",
        "Review context:",
        json.dumps(review_payload, ensure_ascii=False, indent=2),
        "",
        "Predicted candidate:",
        json.dumps(prediction_candidate, ensure_ascii=False, indent=2),
        "",
        "Gold candidate:",
        json.dumps(gold_candidate, ensure_ascii=False, indent=2),
    ]
    return "\n".join(parts)


def parse_judge_response(raw_output: str) -> dict[str, Any]:
    text = raw_output.strip()
    if not text:
        raise ValueError("empty_judge_output")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("judge_json_not_found")
    payload = json.loads(text[start : end + 1])
    verdict = str(payload.get("verdict", "")).strip()
    if verdict not in ALLOWED_VERDICTS:
        raise ValueError(f"invalid_verdict:{verdict}")
    raw_tags = payload.get("reason_tags", [])
    if not isinstance(raw_tags, list):
        raise ValueError("reason_tags_not_list")
    reason_tags: list[str] = []
    for item in raw_tags:
        tag = str(item).strip()
        if not tag:
            continue
        if tag not in ALLOWED_REASON_TAGS:
            raise ValueError(f"invalid_reason_tag:{tag}")
        if tag not in reason_tags:
            reason_tags.append(tag)
    confidence = str(payload.get("confidence", "")).strip().lower()
    if confidence not in {"high", "medium", "low"}:
        raise ValueError(f"invalid_confidence:{confidence}")
    rationale = str(payload.get("rationale", "")).strip()
    if not rationale:
        raise ValueError("empty_rationale")
    return {
        "verdict": verdict,
        "reason_tags": reason_tags,
        "confidence": confidence,
        "rationale": rationale,
    }


def _pair_source_from_indices(
    pred_index: int,
    gold_index: int,
    rigid_matches: dict[tuple[int, int], dict[str, Any]],
    unmatched_pred: set[int],
    unmatched_gold: set[int],
) -> tuple[str, float]:
    match = rigid_matches.get((pred_index, gold_index))
    if match is not None:
        return "rigid_match", float(match.get("score", 0.0))
    if pred_index in unmatched_pred and gold_index in unmatched_gold:
        return "rigid_unmatched_pair", 0.0
    return "rigid_miss_pair", 0.0


def build_judge_pairs(review_result: dict[str, Any]) -> list[JudgePairContext]:
    predictions = review_result.get("normalized_predictions", [])
    golds = review_result.get("normalized_gold", [])
    rigid_matches = {
        (int(match["pred_index"]), int(match["gold_index"])): match
        for match in review_result.get("matches", [])
    }
    unmatched_pred = set(review_result.get("unmatched_prediction_indices", []))
    unmatched_gold = set(review_result.get("unmatched_gold_indices", []))
    if not predictions or not golds:
        return []

    pair_keys: set[tuple[int, int]] = set(rigid_matches)

    for pred_index in unmatched_pred:
        best_gold_index = max(
            range(len(golds)),
            key=lambda gold_index: candidate_similarity(predictions[pred_index], golds[gold_index])[0],
        )
        pair_keys.add((pred_index, best_gold_index))

    for gold_index in unmatched_gold:
        best_pred_index = max(
            range(len(predictions)),
            key=lambda pred_index: candidate_similarity(predictions[pred_index], golds[gold_index])[0],
        )
        pair_keys.add((best_pred_index, gold_index))

    pairs: list[JudgePairContext] = []
    for pred_index, gold_index in sorted(pair_keys):
        pair_source, rigid_score = _pair_source_from_indices(
            pred_index,
            gold_index,
            rigid_matches,
            unmatched_pred,
            unmatched_gold,
        )
        if pair_source != "rigid_match":
            rigid_score = candidate_similarity(predictions[pred_index], golds[gold_index])[0]
        pairs.append(
            JudgePairContext(
                review_id=review_result["review_id"],
                pred_index=pred_index,
                gold_index=gold_index,
                pair_source=pair_source,
                rigid_similarity_score=rigid_score,
                prediction_candidate=predictions[pred_index],
                gold_candidate=golds[gold_index],
            )
        )
    return pairs


def judge_pair(
    backend: ModelBackend,
    config: RunConfig,
    review_row: dict[str, Any],
    pair: JudgePairContext,
) -> dict[str, Any]:
    prompt = build_judge_prompt(review_row, pair.prediction_candidate, pair.gold_candidate)
    request_context = {
        "review_id": pair.review_id,
        "judge_pair_key": f"{pair.review_id}::pred{pair.pred_index}::gold{pair.gold_index}",
    }
    raw_output = backend.generate(prompt, request_context, config)
    parsed = parse_judge_response(raw_output)
    semantic_match = parsed["verdict"] == "equivalent" or (
        parsed["verdict"] == "partially_equivalent" and parsed["confidence"] == "high"
    )
    loose_semantic_match = parsed["verdict"] in {"equivalent", "partially_equivalent"}
    return {
        "review_id": pair.review_id,
        "pred_index": pair.pred_index,
        "gold_index": pair.gold_index,
        "pair_source": pair.pair_source,
        "rigid_similarity_score": pair.rigid_similarity_score,
        "judge_verdict": parsed["verdict"],
        "judge_reason_tags": parsed["reason_tags"],
        "judge_confidence": parsed["confidence"],
        "judge_rationale": parsed["rationale"],
        "semantic_match": semantic_match,
        "loose_semantic_match": loose_semantic_match,
    }


def _max_bipartite_match(edges: dict[int, list[int]]) -> int:
    matched_gold: dict[int, int] = {}

    def _dfs(pred_index: int, seen: set[int]) -> bool:
        for gold_index in edges.get(pred_index, []):
            if gold_index in seen:
                continue
            seen.add(gold_index)
            owner = matched_gold.get(gold_index)
            if owner is None or _dfs(owner, seen):
                matched_gold[gold_index] = pred_index
                return True
        return False

    matched = 0
    for pred_index in sorted(edges):
        if _dfs(pred_index, set()):
            matched += 1
    return matched


def summarize_judge_review(
    review_result: dict[str, Any],
    pair_results: list[dict[str, Any]],
) -> dict[str, Any]:
    strict_edges: dict[int, list[int]] = {}
    loose_edges: dict[int, list[int]] = {}
    reason_tag_counts: dict[str, int] = {tag: 0 for tag in ALLOWED_REASON_TAGS}
    rigid_fail_but_semantic_match_count = 0
    canonicalization_rescue_count = 0
    for item in pair_results:
        if item["semantic_match"]:
            strict_edges.setdefault(int(item["pred_index"]), []).append(int(item["gold_index"]))
            if item["pair_source"] != "rigid_match":
                rigid_fail_but_semantic_match_count += 1
        if item["loose_semantic_match"]:
            loose_edges.setdefault(int(item["pred_index"]), []).append(int(item["gold_index"]))
        if item["pair_source"] == "rigid_match" and item["semantic_match"]:
            canonicalization_rescue_count += 1
        for tag in item["judge_reason_tags"]:
            reason_tag_counts[tag] = reason_tag_counts.get(tag, 0) + 1
    pred_count = int(review_result.get("pred_candidate_count", 0))
    gold_count = int(review_result.get("gold_candidate_count", 0))
    strict_match_count = _max_bipartite_match(strict_edges)
    loose_match_count = _max_bipartite_match(loose_edges)
    strict_precision = strict_match_count / pred_count if pred_count else 0.0
    strict_recall = strict_match_count / gold_count if gold_count else 0.0
    loose_precision = loose_match_count / pred_count if pred_count else 0.0
    loose_recall = loose_match_count / gold_count if gold_count else 0.0
    return {
        "review_id": review_result["review_id"],
        "pred_candidate_count": pred_count,
        "gold_candidate_count": gold_count,
        "semantic_strict_match_count": strict_match_count,
        "semantic_loose_match_count": loose_match_count,
        "semantic_review_covered": strict_match_count > 0,
        "strict_semantic_candidate_precision": strict_precision,
        "strict_semantic_candidate_recall": strict_recall,
        "strict_semantic_candidate_f1": _safe_f1(strict_precision, strict_recall),
        "loose_semantic_candidate_precision": loose_precision,
        "loose_semantic_candidate_recall": loose_recall,
        "loose_semantic_candidate_f1": _safe_f1(loose_precision, loose_recall),
        "rigid_fail_but_semantic_match_count": rigid_fail_but_semantic_match_count,
        "canonicalization_rescue_count": canonicalization_rescue_count,
        "judge_reason_tag_counts": reason_tag_counts,
        "pair_results": pair_results,
    }


def aggregate_judge_results(review_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if not review_summaries:
        return {}
    total_pred = sum(item["pred_candidate_count"] for item in review_summaries)
    total_gold = sum(item["gold_candidate_count"] for item in review_summaries)
    total_strict = sum(item["semantic_strict_match_count"] for item in review_summaries)
    total_loose = sum(item["semantic_loose_match_count"] for item in review_summaries)
    total_rigid_fail_semantic = sum(item["rigid_fail_but_semantic_match_count"] for item in review_summaries)
    total_canonicalization_rescue = sum(item["canonicalization_rescue_count"] for item in review_summaries)
    matched_pairs = sum(
        1
        for item in review_summaries
        for pair in item["pair_results"]
        if pair["pair_source"] == "rigid_match"
    )
    tag_counts: dict[str, int] = {tag: 0 for tag in ALLOWED_REASON_TAGS}
    for item in review_summaries:
        for tag, count in item["judge_reason_tag_counts"].items():
            tag_counts[tag] = tag_counts.get(tag, 0) + int(count)
    strict_precision = total_strict / total_pred if total_pred else 0.0
    strict_recall = total_strict / total_gold if total_gold else 0.0
    loose_precision = total_loose / total_pred if total_pred else 0.0
    loose_recall = total_loose / total_gold if total_gold else 0.0
    return {
        "review_count": len(review_summaries),
        "judge_version": JUDGE_VERSION,
        "semantic_matched_review_count": sum(1 for item in review_summaries if item["semantic_review_covered"]),
        "semantic_candidate_precision": strict_precision,
        "semantic_candidate_recall": strict_recall,
        "semantic_candidate_f1": _safe_f1(strict_precision, strict_recall),
        "strict_semantic_match_count": total_strict,
        "strict_semantic_candidate_precision": strict_precision,
        "strict_semantic_candidate_recall": strict_recall,
        "strict_semantic_candidate_f1": _safe_f1(strict_precision, strict_recall),
        "loose_semantic_match_count": total_loose,
        "loose_semantic_candidate_precision": loose_precision,
        "loose_semantic_candidate_recall": loose_recall,
        "loose_semantic_candidate_f1": _safe_f1(loose_precision, loose_recall),
        "rigid_fail_but_semantic_match_count": total_rigid_fail_semantic,
        "canonicalization_rescue_rate": (total_canonicalization_rescue / matched_pairs if matched_pairs else 0.0),
        "judge_reason_tag_counts": tag_counts,
    }


def build_judge_error_analysis(review_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for review in review_summaries:
        for pair in review.get("pair_results", []):
            if pair["semantic_match"]:
                continue
            rows.append(
                {
                    "review_id": review["review_id"],
                    "pred_index": pair["pred_index"],
                    "gold_index": pair["gold_index"],
                    "pair_source": pair["pair_source"],
                    "judge_verdict": pair["judge_verdict"],
                    "judge_reason_tags": pair["judge_reason_tags"],
                    "judge_confidence": pair["judge_confidence"],
                    "judge_rationale": pair["judge_rationale"],
                }
            )
    return rows


def build_rigid_review_result(
    review_row: dict[str, Any],
    prediction_payload: dict[str, Any],
    *,
    split: str,
    threshold: float,
    prediction_mode: str,
) -> dict[str, Any]:
    if prediction_mode == "raw":
        candidates = prediction_payload.get("raw_parsed_prediction_json")
        raw_fallback_used = False
        if candidates is None:
            candidates = prediction_payload.get("parsed_prediction_json", [])
            raw_fallback_used = True
    elif prediction_mode == "canonicalized":
        candidates = prediction_payload.get("canonicalized_prediction_json")
        if candidates is None:
            candidates = prediction_payload.get("parsed_prediction_json", [])
        raw_fallback_used = False
    else:
        raise ValueError(f"unknown_prediction_mode:{prediction_mode}")
    result = evaluate_review(
        review_row["review_id"],
        list(candidates or []),
        review_row.get("gold_partial_analysis_settings", []),
        review_row.get("metadata", {}),
        split=split,
        threshold=threshold,
        schema_valid=prediction_payload.get("schema_valid", False),
        parse_status=prediction_payload.get("parse_status", "missing_prediction"),
    )
    result["prediction_mode"] = prediction_mode
    result["raw_prediction_fallback_used"] = raw_fallback_used
    result["canonicalization_provenance"] = prediction_payload.get("canonicalization_provenance", {})
    return result
