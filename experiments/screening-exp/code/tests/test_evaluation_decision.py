from __future__ import annotations

import csv
import subprocess
import sys

import pytest

from screening.evaluation.decision import evaluate_predictions
from screening.evaluation.tables import metrics_to_readiness_row, update_automation_readiness_table
from screening.io_utils import read_json, write_json, write_model_jsonl
from screening.schemas import (
    AbstractScreeningPrediction,
    InputSetting,
    ScreeningExample,
    ScreeningPrediction,
)


def _example(example_id: str, gold_decision: str) -> ScreeningExample:
    return ScreeningExample(
        example_id=example_id,
        benchmark="q2crbench",
        split="test",
        review_id="review-1",
        study_id=example_id,
        title="Trial title",
        abstract="Trial abstract",
        input_setting=InputSetting.abstract_only,
        gold_decision=gold_decision,
    )


def _prediction(
    example_id: str,
    decision: str,
    *,
    sent_to_full_text: bool | None = None,
) -> ScreeningPrediction:
    metadata = {}
    if sent_to_full_text is not None:
        metadata["sent_to_full_text"] = sent_to_full_text
    return ScreeningPrediction(
        example_id=example_id,
        decision=decision,
        metadata=metadata,
    )


def test_evaluate_predictions_binary_counts() -> None:
    examples = [
        _example("include-hit", "include"),
        _example("exclude-hit", "exclude"),
        _example("exclude-fp", "exclude"),
        _example("include-fn", "include"),
    ]
    predictions = [
        _prediction("include-hit", "include"),
        _prediction("exclude-hit", "exclude"),
        _prediction("exclude-fp", "include"),
        _prediction("include-fn", "exclude"),
    ]

    metrics = evaluate_predictions(
        predictions=predictions,
        examples=examples,
        run_id="run-1",
        method="direct",
        readiness_profile="stage1",
    )

    assert metrics["counts"] == {"tp": 1, "tn": 1, "fp": 1, "fn": 1, "total": 4}
    assert metrics["decision_metrics"]["sensitivity"] == pytest.approx(1 / 2)
    assert metrics["decision_metrics"]["specificity"] == pytest.approx(1 / 2)
    assert metrics["decision_metrics"]["precision"] == pytest.approx(1 / 2)
    assert metrics["decision_metrics"]["balanced_accuracy"] == pytest.approx(1 / 2)
    assert metrics["decision_metrics"]["macro_f1"] == pytest.approx(1 / 2)
    assert metrics["decision_metrics"]["false_negative_count"] == 1
    assert metrics["readiness"]["decision_ready"] is False
    assert metrics["readiness"]["overall_ready"] is False


def test_safety_metrics_keep_confidence_placeholders_null() -> None:
    examples = [_example("include-fn", "include")]
    predictions = [_prediction("include-fn", "exclude")]

    metrics = evaluate_predictions(
        predictions=predictions,
        examples=examples,
        run_id="run-default",
        method="direct",
    )

    assert metrics["safety_metrics"]["high_confidence_threshold"] is None
    assert metrics["safety_metrics"]["high_confidence_false_negative_count"] is None


def test_evaluate_predictions_accepts_abstract_minimal_predictions() -> None:
    examples = [_example("example-1", "include")]
    predictions = [
        AbstractScreeningPrediction(
            example_id="example-1",
            decision="include",
            main_reason="Abstract remains plausibly relevant.",
        )
    ]

    metrics = evaluate_predictions(
        predictions=predictions,
        examples=examples,
        run_id="run-abstract-minimal",
        method="direct",
        readiness_profile="stage1",
    )

    assert metrics["counts"] == {"tp": 1, "tn": 0, "fp": 0, "fn": 0, "total": 1}
    assert metrics["decision_metrics"]["sensitivity"] == 1.0


def test_reason_metrics_are_placeholder_nulls() -> None:
    metrics = evaluate_predictions(
        predictions=[_prediction("example-1", "exclude")],
        examples=[_example("example-1", "exclude")],
        run_id="run-1",
        method="direct",
        readiness_profile="full_text",
        workload_mode="one",
    )

    assert metrics["safety_metrics"]["unsupported_exclusion_rate"] is None
    assert metrics["safety_metrics"]["hallucinated_reason_rate"] is None
    assert metrics["safety_metrics"]["placeholder_status"] == "not_evaluated"
    assert metrics["readiness"]["blocked_by_placeholder"] is True
    assert metrics["readiness"]["overall_ready"] is False
    assert "reason_metrics_not_implemented" in metrics["readiness"]["failed_checks"]


def test_two_stage_readiness_uses_prediction_workload_and_reference() -> None:
    examples = [
        _example("include-hit", "include"),
        _example("exclude-hit", "exclude"),
        _example("include-fn", "include"),
    ]
    predictions = [
        _prediction("include-hit", "include", sent_to_full_text=True),
        _prediction("exclude-hit", "exclude", sent_to_full_text=False),
        _prediction("include-fn", "include", sent_to_full_text=True),
    ]
    reference_metrics = {"decision_metrics": {"sensitivity": 0.99}}

    metrics = evaluate_predictions(
        predictions=predictions,
        examples=examples,
        run_id="run-two-stage",
        method="two-stage",
        readiness_profile="two_stage",
        workload_mode="from_predictions",
        reference_metrics=reference_metrics,
    )

    assert metrics["workload_metrics"]["full_text_workload"] == pytest.approx(2 / 3)
    assert metrics["workload_metrics"]["full_text_workload_reduction"] == pytest.approx(1 / 3)
    assert metrics["readiness"]["reference_sensitivity"] == 0.99
    assert metrics["readiness"]["sensitivity_gap_vs_reference"] == pytest.approx(0.0)
    assert metrics["readiness"]["overall_ready"] is True


def test_duplicate_prediction_ids_raise() -> None:
    examples = [_example("example-1", "include")]
    predictions = [
        _prediction("example-1", "include"),
        _prediction("example-1", "exclude"),
    ]

    with pytest.raises(ValueError, match="duplicate example_id"):
        evaluate_predictions(
            predictions=predictions,
            examples=examples,
            run_id="run-dup",
            method="direct",
        )


def test_readiness_row_round_trip_and_upsert(tmp_path) -> None:
    metrics = evaluate_predictions(
        predictions=[_prediction("example-1", "include")],
        examples=[_example("example-1", "include")],
        run_id="run-1",
        method="direct",
        readiness_profile="stage1",
    )
    row = metrics_to_readiness_row(metrics)
    assert row["run_id"] == "run-1"
    assert row["readiness_profile"] == "stage1"

    table_path = tmp_path / "automation_readiness.csv"
    update_automation_readiness_table(table_path, metrics)
    updated_metrics = evaluate_predictions(
        predictions=[_prediction("example-1", "exclude")],
        examples=[_example("example-1", "include")],
        run_id="run-1",
        method="direct",
        readiness_profile="stage1",
    )
    update_automation_readiness_table(table_path, updated_metrics)

    with table_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["high_confidence_false_negative_count"] == ""


def test_cli_evaluate_predictions_end_to_end(tmp_path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    gold_path = tmp_path / "gold.jsonl"
    output_path = tmp_path / "metrics.json"
    defaults_path = tmp_path / "defaults.yaml"
    examples = [
        _example("example-1", "include"),
        _example("example-2", "exclude"),
    ]
    predictions = [
        _prediction("example-1", "exclude"),
        _prediction("example-2", "exclude"),
    ]
    write_model_jsonl(predictions_path, predictions)
    write_model_jsonl(gold_path, examples)
    defaults_path.write_text(
        "default_provider: openai\nprompt_version: v0\noutput_root: results\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "screening.cli.evaluate_predictions",
            "--predictions",
            str(predictions_path),
            "--gold",
            str(gold_path),
            "--output",
            str(output_path),
            "--defaults-config",
            str(defaults_path),
            "--method",
            "direct",
            "--run-id",
            "cli-run",
            "--readiness-profile",
            "stage1",
            "--workload-mode",
            "zero",
            "--no-append-readiness-table",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    metrics = read_json(output_path)
    assert metrics["metadata"]["run_id"] == "cli-run"
    assert metrics["safety_metrics"]["high_confidence_threshold"] is None


def test_cli_two_stage_requires_reference_for_readiness(tmp_path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    gold_path = tmp_path / "gold.jsonl"
    output_path = tmp_path / "metrics.json"
    examples = [_example("example-1", "include")]
    predictions = [_prediction("example-1", "include", sent_to_full_text=True)]
    write_model_jsonl(predictions_path, predictions)
    write_model_jsonl(gold_path, examples)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "screening.cli.evaluate_predictions",
            "--predictions",
            str(predictions_path),
            "--gold",
            str(gold_path),
            "--output",
            str(output_path),
            "--method",
            "two-stage",
            "--run-id",
            "two-stage-cli",
            "--readiness-profile",
            "two_stage",
            "--workload-mode",
            "from_predictions",
            "--no-append-readiness-table",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    metrics = read_json(output_path)
    assert metrics["readiness"]["overall_ready"] is False
    assert "sensitivity_within_reference_gap" in metrics["readiness"]["failed_checks"]


def test_write_json_reference_metrics_round_trip(tmp_path) -> None:
    path = tmp_path / "reference.json"
    write_json(path, {"decision_metrics": {"sensitivity": 0.95}})
    assert read_json(path)["decision_metrics"]["sensitivity"] == 0.95
