"""Decision, safety, workload, and readiness evaluation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

from screening.schemas import (
    BaseScreeningPrediction,
    Decision,
    GoldDecision,
    InputSetting,
    ScreeningExample,
)

DEFAULT_TWO_STAGE_SENSITIVITY_GAP = 0.01
RecordT = TypeVar("RecordT")


def _safe_divide(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _average(values: Iterable[float | None]) -> float | None:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _normalized_prediction_decision(prediction: BaseScreeningPrediction) -> GoldDecision:
    return GoldDecision.exclude if prediction.decision == Decision.exclude else GoldDecision.include


def _example_input_setting(examples: list[ScreeningExample]) -> InputSetting | None:
    settings = {example.input_setting for example in examples if example.input_setting is not None}
    if len(settings) == 1:
        return next(iter(settings))
    return None


def _build_unique_index(records: Iterable[RecordT], key_name: str) -> dict[str, RecordT]:
    index: dict[str, RecordT] = {}
    for record in records:
        key = getattr(record, key_name)
        if key in index:
            raise ValueError(f"duplicate {key_name}: {key}")
        index[key] = record
    return index


def _compute_workload_metrics(
    *,
    examples: list[ScreeningExample],
    predictions: list[BaseScreeningPrediction],
    workload_mode: str,
) -> dict[str, Any]:
    if workload_mode not in {"auto", "zero", "one", "from_predictions"}:
        raise ValueError(f"unsupported workload_mode: {workload_mode}")

    input_setting = _example_input_setting(examples)
    resolved_mode = workload_mode
    workload: float | None = None

    if workload_mode == "auto":
        if input_setting == InputSetting.abstract_only:
            resolved_mode = "zero"
        elif input_setting in {
            InputSetting.full_text_only,
            InputSetting.abstract_plus_full_text,
            InputSetting.evidence_profile,
        }:
            resolved_mode = "one"
        else:
            resolved_mode = "from_predictions"

    if resolved_mode == "zero":
        workload = 0.0
    elif resolved_mode == "one":
        workload = 1.0
    else:
        sent_flags: list[bool] = []
        missing = False
        for prediction in predictions:
            value = prediction.metadata.get("sent_to_full_text")
            if isinstance(value, bool):
                sent_flags.append(value)
            else:
                missing = True
                break
        if not missing:
            workload = sum(1 for value in sent_flags if value) / len(predictions) if predictions else None

    reduction = None if workload is None else 1.0 - workload
    return {
        "full_text_workload": workload,
        "full_text_workload_reduction": reduction,
        "workload_source": resolved_mode,
    }


def _build_check(name: str, passed: bool, *, actual: Any, threshold: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "actual": actual,
        "threshold": threshold,
    }


def _evaluate_readiness(
    *,
    readiness_profile: str,
    decision_metrics: dict[str, Any],
    safety_metrics: dict[str, Any],
    workload_metrics: dict[str, Any],
    reference_metrics: dict[str, Any] | None,
    two_stage_sensitivity_gap: float,
) -> dict[str, Any]:
    sensitivity = decision_metrics["sensitivity"]
    balanced_accuracy = decision_metrics["balanced_accuracy"]
    full_text_workload = workload_metrics["full_text_workload"]
    checks: list[dict[str, Any]] = []
    failed_checks: list[str] = []
    reference_sensitivity = None
    sensitivity_gap_vs_reference = None
    decision_ready: bool | None = None
    overall_ready: bool | None = None
    blocked_by_placeholder = False

    def record_check(name: str, passed: bool, *, actual: Any, threshold: Any) -> None:
        checks.append(_build_check(name, passed, actual=actual, threshold=threshold))
        if not passed:
            failed_checks.append(name)

    if readiness_profile == "none":
        return {
            "profile": readiness_profile,
            "checks": checks,
            "decision_ready": None,
            "overall_ready": None,
            "failed_checks": failed_checks,
            "blocked_by_placeholder": False,
            "reference_sensitivity": None,
            "sensitivity_gap_vs_reference": None,
        }

    if readiness_profile == "stage1":
        record_check(
            "sensitivity_gte_0.98",
            sensitivity is not None and sensitivity >= 0.98,
            actual=sensitivity,
            threshold=">=0.98",
        )
        record_check(
            "false_negative_count_eq_0",
            decision_metrics["false_negative_count"] == 0,
            actual=decision_metrics["false_negative_count"],
            threshold="==0",
        )
        decision_ready = not failed_checks
        overall_ready = decision_ready
    elif readiness_profile == "full_text":
        record_check(
            "sensitivity_gte_0.95",
            sensitivity is not None and sensitivity >= 0.95,
            actual=sensitivity,
            threshold=">=0.95",
        )
        record_check(
            "balanced_accuracy_gte_0.80",
            balanced_accuracy is not None and balanced_accuracy >= 0.80,
            actual=balanced_accuracy,
            threshold=">=0.80",
        )
        record_check(
            "false_negative_count_eq_0",
            decision_metrics["false_negative_count"] == 0,
            actual=decision_metrics["false_negative_count"],
            threshold="==0",
        )
        decision_ready = not failed_checks
        blocked_by_placeholder = True
        overall_ready = False
        failed_checks.append("reason_metrics_not_implemented")
    elif readiness_profile == "two_stage":
        record_check(
            "false_negative_count_eq_0",
            decision_metrics["false_negative_count"] == 0,
            actual=decision_metrics["false_negative_count"],
            threshold="==0",
        )
        record_check(
            "full_text_workload_lt_1.0",
            full_text_workload is not None and full_text_workload < 1.0,
            actual=full_text_workload,
            threshold="<1.0",
        )
        if reference_metrics is not None:
            reference_sensitivity = reference_metrics.get("decision_metrics", {}).get("sensitivity")
        sensitivity_gap_ok = False
        if sensitivity is not None and reference_sensitivity is not None:
            sensitivity_gap_vs_reference = max(reference_sensitivity - sensitivity, 0.0)
            sensitivity_gap_ok = sensitivity_gap_vs_reference <= two_stage_sensitivity_gap
        record_check(
            "sensitivity_within_reference_gap",
            sensitivity_gap_ok,
            actual=sensitivity_gap_vs_reference,
            threshold=f"<={two_stage_sensitivity_gap}",
        )
        decision_ready = not failed_checks
        overall_ready = decision_ready
    else:
        raise ValueError(f"unsupported readiness_profile: {readiness_profile}")

    return {
        "profile": readiness_profile,
        "checks": checks,
        "decision_ready": decision_ready,
        "overall_ready": overall_ready,
        "failed_checks": failed_checks,
        "blocked_by_placeholder": blocked_by_placeholder,
        "reference_sensitivity": reference_sensitivity,
        "sensitivity_gap_vs_reference": sensitivity_gap_vs_reference,
    }


def evaluate_predictions(
    *,
    predictions: list[BaseScreeningPrediction],
    examples: list[ScreeningExample],
    run_id: str,
    method: str,
    predictions_path: str | None = None,
    gold_path: str | None = None,
    benchmark: str | None = None,
    split: str | None = None,
    input_setting: str | None = None,
    readiness_profile: str = "none",
    workload_mode: str = "auto",
    reference_metrics: dict[str, Any] | None = None,
    two_stage_sensitivity_gap: float = DEFAULT_TWO_STAGE_SENSITIVITY_GAP,
) -> dict[str, Any]:
    """Evaluate aligned predictions against gold labels."""
    if not predictions:
        raise ValueError("predictions must not be empty")
    if not examples:
        raise ValueError("examples must not be empty")

    prediction_index = _build_unique_index(predictions, "example_id")
    example_index = _build_unique_index(examples, "example_id")

    missing_predictions = sorted(set(example_index) - set(prediction_index))
    extra_predictions = sorted(set(prediction_index) - set(example_index))
    if missing_predictions:
        raise ValueError(f"missing predictions for example_ids: {', '.join(missing_predictions[:5])}")
    if extra_predictions:
        raise ValueError(f"predictions without gold example_ids: {', '.join(extra_predictions[:5])}")

    aligned_examples: list[ScreeningExample] = []
    aligned_predictions: list[BaseScreeningPrediction] = []
    for example_id, example in example_index.items():
        if example.gold_decision is None:
            raise ValueError(f"gold_decision is required for example_id: {example_id}")
        aligned_examples.append(example)
        aligned_predictions.append(prediction_index[example_id])

    tp = tn = fp = fn = 0
    for example, prediction in zip(aligned_examples, aligned_predictions, strict=True):
        gold = example.gold_decision
        predicted = _normalized_prediction_decision(prediction)
        if gold == GoldDecision.include and predicted == GoldDecision.include:
            tp += 1
        elif gold == GoldDecision.exclude and predicted == GoldDecision.exclude:
            tn += 1
        elif gold == GoldDecision.exclude and predicted == GoldDecision.include:
            fp += 1
        else:
            fn += 1

    sensitivity = _safe_divide(tp, tp + fn)
    specificity = _safe_divide(tn, tn + fp)
    precision = _safe_divide(tp, tp + fp)
    include_f1 = (
        None
        if precision is None or sensitivity is None or precision + sensitivity == 0
        else 2 * precision * sensitivity / (precision + sensitivity)
    )
    exclude_precision = _safe_divide(tn, tn + fn)
    exclude_recall = specificity
    exclude_f1 = (
        None
        if exclude_precision is None
        or exclude_recall is None
        or exclude_precision + exclude_recall == 0
        else 2 * exclude_precision * exclude_recall / (exclude_precision + exclude_recall)
    )
    decision_metrics = {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "balanced_accuracy": _average([sensitivity, specificity]),
        "macro_f1": _average([include_f1, exclude_f1]),
        "false_negative_count": fn,
    }
    safety_metrics = {
        "high_confidence_threshold": None,
        "high_confidence_false_negative_count": None,
        "high_confidence_false_negative_ids": [],
        "unsupported_exclusion_count": None,
        "unsupported_exclusion_rate": None,
        "hallucinated_reason_count": None,
        "hallucinated_reason_rate": None,
        "placeholder_status": "not_evaluated",
    }
    workload_metrics = _compute_workload_metrics(
        examples=aligned_examples,
        predictions=aligned_predictions,
        workload_mode=workload_mode,
    )
    resolved_benchmark = benchmark or (aligned_examples[0].benchmark if aligned_examples else None)
    resolved_split = split or (aligned_examples[0].split if aligned_examples else None)
    resolved_input_setting = input_setting or (
        aligned_examples[0].input_setting.value
        if aligned_examples and aligned_examples[0].input_setting is not None
        else None
    )
    readiness = _evaluate_readiness(
        readiness_profile=readiness_profile,
        decision_metrics=decision_metrics,
        safety_metrics=safety_metrics,
        workload_metrics=workload_metrics,
        reference_metrics=reference_metrics,
        two_stage_sensitivity_gap=two_stage_sensitivity_gap,
    )
    return {
        "counts": {
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "total": len(aligned_examples),
        },
        "decision_metrics": decision_metrics,
        "safety_metrics": safety_metrics,
        "workload_metrics": workload_metrics,
        "readiness": readiness,
        "metadata": {
            "run_id": run_id,
            "method": method,
            "benchmark": resolved_benchmark,
            "split": resolved_split,
            "input_setting": resolved_input_setting,
            "predictions_path": predictions_path,
            "gold_path": gold_path,
        },
    }
