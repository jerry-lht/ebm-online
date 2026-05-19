"""Conservative two-stage screening policy composition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from screening.schemas import (
    BaseScreeningPrediction,
    Decision,
    RawResponseMetadata,
    ScreeningExample,
    ScreeningPrediction,
)

TWO_STAGE_POLICY_NAME = "conservative_stage1_exclude_only_v1"


@dataclass(frozen=True)
class TwoStageArtifacts:
    """In-memory artifacts emitted by the two-stage policy."""

    predictions: list[ScreeningPrediction]
    stage1_actions: list[dict[str, Any]]
    stage2_inputs: list[ScreeningExample]
    missing_stage2_predictions: list[dict[str, Any]]


def _example_key(example: ScreeningExample) -> tuple[str, str, str, str]:
    return (example.benchmark, example.split, example.review_id, example.study_id)


def _build_prediction_index(
    predictions: list[BaseScreeningPrediction],
    *,
    role: str,
) -> dict[str, BaseScreeningPrediction]:
    index: dict[str, BaseScreeningPrediction] = {}
    for prediction in predictions:
        if prediction.example_id in index:
            raise ValueError(f"duplicate {role} prediction example_id: {prediction.example_id}")
        index[prediction.example_id] = prediction
    return index


def _build_example_key_index(
    examples: list[ScreeningExample],
    *,
    role: str,
) -> dict[tuple[str, str, str, str], ScreeningExample]:
    index: dict[tuple[str, str, str, str], ScreeningExample] = {}
    for example in examples:
        key = _example_key(example)
        if key in index:
            key_text = "::".join(key)
            raise ValueError(f"duplicate {role} example key: {key_text}")
        index[key] = example
    return index


def _prediction_main_reason(prediction: BaseScreeningPrediction | None) -> str | None:
    if prediction is None:
        return None
    value = getattr(prediction, "main_reason", None)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _trace_metadata(
    *,
    run_id: str,
    stage1_example: ScreeningExample,
    stage2_example: ScreeningExample,
    stage1_prediction: BaseScreeningPrediction | None,
    stage1_action: str,
    stage2_prediction: BaseScreeningPrediction | None,
    stage2_method: str,
    sent_to_full_text: bool,
    finalization_reason: str,
    source_paths: dict[str, str],
) -> dict[str, Any]:
    stage1_decision = stage1_prediction.decision.value if stage1_prediction else None
    stage2_decision = stage2_prediction.decision.value if stage2_prediction else None
    needs_review = finalization_reason in {
        "missing_stage1_prediction",
        "missing_stage2_prediction",
    }
    return {
        "run_id": run_id,
        "two_stage_policy": TWO_STAGE_POLICY_NAME,
        "stage1_decision": stage1_decision,
        "stage1_action": stage1_action,
        "stage2_decision": stage2_decision,
        "stage2_method": stage2_method,
        "sent_to_full_text": sent_to_full_text,
        "needs_review": needs_review,
        "needs_review_reason": finalization_reason if needs_review else None,
        "finalization_reason": finalization_reason,
        "stage1_example_id": stage1_example.example_id,
        "stage2_example_id": stage2_example.example_id,
        "stage1_prediction_path": source_paths["stage1_predictions"],
        "stage2_prediction_path": source_paths["stage2_predictions"],
        "stage1_examples_path": source_paths["stage1_examples"],
        "stage2_examples_path": source_paths["stage2_examples"],
    }


def _screening_prediction_from_source(
    *,
    source_prediction: BaseScreeningPrediction | None,
    final_example_id: str,
    decision: Decision,
    main_reason: str,
    metadata: dict[str, Any],
) -> ScreeningPrediction:
    if source_prediction is not None:
        payload = source_prediction.model_dump(mode="python")
    else:
        payload = {
            "example_id": final_example_id,
            "decision": decision,
            "raw_response_metadata": RawResponseMetadata(),
            "metadata": {},
        }
    payload["example_id"] = final_example_id
    payload["decision"] = decision
    payload["metadata"] = {**payload.get("metadata", {}), **metadata}
    payload["main_reason"] = _prediction_main_reason(source_prediction) or main_reason
    payload.setdefault("criterion_judgments", {})
    payload.setdefault("failed_criterion", None)
    payload.setdefault("evidence_spans", [])
    return ScreeningPrediction.model_validate(payload)


def combine_two_stage_predictions(
    *,
    stage1_examples: list[ScreeningExample],
    stage1_predictions: list[BaseScreeningPrediction],
    stage2_examples: list[ScreeningExample],
    stage2_predictions: list[BaseScreeningPrediction],
    stage2_method: str,
    run_id: str,
    stage1_examples_path: str | Path,
    stage1_predictions_path: str | Path,
    stage2_examples_path: str | Path,
    stage2_predictions_path: str | Path,
) -> TwoStageArtifacts:
    """Compose abstract-only and full-text predictions into final decisions.

    The full-text-capable stage2 examples define the evaluation cohort. Extra
    abstract-only stage1 examples are allowed because CSMeD-FT dev contains a
    few abstract records without full text; every stage2 example must still map
    to exactly one stage1 example by benchmark/split/review_id/study_id.
    """
    if not stage1_examples:
        raise ValueError("stage1_examples must not be empty")
    if not stage2_examples:
        raise ValueError("stage2_examples must not be empty")

    stage1_example_index = _build_example_key_index(stage1_examples, role="stage1")
    stage2_example_index = _build_example_key_index(stage2_examples, role="stage2")
    stage1_prediction_index = _build_prediction_index(stage1_predictions, role="stage1")
    stage2_prediction_index = _build_prediction_index(stage2_predictions, role="stage2")

    missing_stage1_examples = [
        "::".join(key) for key in stage2_example_index if key not in stage1_example_index
    ]
    if missing_stage1_examples:
        sample = ", ".join(missing_stage1_examples[:5])
        raise ValueError(f"stage2 examples without matching stage1 examples: {sample}")

    source_paths = {
        "stage1_examples": str(stage1_examples_path),
        "stage1_predictions": str(stage1_predictions_path),
        "stage2_examples": str(stage2_examples_path),
        "stage2_predictions": str(stage2_predictions_path),
    }

    final_predictions: list[ScreeningPrediction] = []
    stage1_actions: list[dict[str, Any]] = []
    stage2_inputs: list[ScreeningExample] = []
    missing_stage2_predictions: list[dict[str, Any]] = []

    for stage2_example in stage2_examples:
        stage1_example = stage1_example_index[_example_key(stage2_example)]
        stage1_prediction = stage1_prediction_index.get(stage1_example.example_id)
        stage2_prediction: BaseScreeningPrediction | None = None

        if stage1_prediction is None:
            stage1_action = "needs_review_missing_stage1_prediction"
            sent_to_full_text = False
            final_decision = Decision.include
            finalization_reason = "missing_stage1_prediction"
            source_prediction = None
            fallback_reason = "Stage 1 prediction is missing; conservatively include for review."
        elif stage1_prediction.decision == Decision.exclude:
            stage1_action = "auto_exclude"
            sent_to_full_text = False
            final_decision = Decision.exclude
            finalization_reason = "stage1_exclude"
            source_prediction = stage1_prediction
            fallback_reason = "Stage 1 excluded this record."
        else:
            stage1_action = "send_to_stage2"
            sent_to_full_text = True
            stage2_inputs.append(stage2_example)
            stage2_prediction = stage2_prediction_index.get(stage2_example.example_id)
            if stage2_prediction is None:
                final_decision = Decision.include
                finalization_reason = "missing_stage2_prediction"
                source_prediction = None
                fallback_reason = "Stage 2 prediction is missing; conservatively include for review."
                missing_stage2_predictions.append(
                    {
                        "stage1_example_id": stage1_example.example_id,
                        "stage2_example_id": stage2_example.example_id,
                        "stage1_decision": stage1_prediction.decision.value,
                        "stage2_method": stage2_method,
                        "reason": finalization_reason,
                    }
                )
            else:
                final_decision = stage2_prediction.decision
                finalization_reason = "stage2_prediction"
                source_prediction = stage2_prediction
                fallback_reason = "Stage 2 prediction used as final decision."

        metadata = _trace_metadata(
            run_id=run_id,
            stage1_example=stage1_example,
            stage2_example=stage2_example,
            stage1_prediction=stage1_prediction,
            stage1_action=stage1_action,
            stage2_prediction=stage2_prediction,
            stage2_method=stage2_method,
            sent_to_full_text=sent_to_full_text,
            finalization_reason=finalization_reason,
            source_paths=source_paths,
        )
        final_prediction = _screening_prediction_from_source(
            source_prediction=source_prediction,
            final_example_id=stage2_example.example_id,
            decision=final_decision,
            main_reason=fallback_reason,
            metadata=metadata,
        )
        final_predictions.append(final_prediction)
        stage1_actions.append(
            {
                "stage1_example_id": stage1_example.example_id,
                "stage2_example_id": stage2_example.example_id,
                "stage1_decision": (
                    stage1_prediction.decision.value if stage1_prediction is not None else None
                ),
                "stage1_action": stage1_action,
                "stage2_decision": stage2_prediction.decision.value if stage2_prediction else None,
                "stage2_method": stage2_method,
                "sent_to_full_text": sent_to_full_text,
                "final_decision": final_decision.value,
                "finalization_reason": finalization_reason,
                "needs_review": metadata["needs_review"],
            }
        )

    return TwoStageArtifacts(
        predictions=final_predictions,
        stage1_actions=stage1_actions,
        stage2_inputs=stage2_inputs,
        missing_stage2_predictions=missing_stage2_predictions,
    )
