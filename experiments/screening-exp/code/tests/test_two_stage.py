from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from screening.io_utils import read_json, read_jsonl, write_model_jsonl
from screening.pipeline.two_stage import combine_two_stage_predictions
from screening.schemas import (
    AbstractScreeningPrediction,
    InputSetting,
    ScreeningExample,
    ScreeningPrediction,
)


def _example(
    study_id: str,
    *,
    setting: InputSetting,
    gold_decision: str = "include",
) -> ScreeningExample:
    return ScreeningExample(
        example_id=f"csmed_ft::dev::review-1::{study_id}::{setting.value}",
        benchmark="csmed_ft",
        split="dev",
        review_id="review-1",
        study_id=study_id,
        title="Trial title",
        abstract="Trial abstract",
        full_text_sections=[{"text": "Full text section"}]
        if setting == InputSetting.abstract_plus_full_text
        else [],
        input_setting=setting,
        gold_decision=gold_decision,
    )


def _stage1_prediction(study_id: str, decision: str) -> AbstractScreeningPrediction:
    return AbstractScreeningPrediction(
        example_id=f"csmed_ft::dev::review-1::{study_id}::abstract_only",
        decision=decision,
        main_reason=f"Stage 1 says {decision}.",
        metadata={
            "input_setting": "abstract_only",
            "prediction_schema": "abstract_only_v3",
        },
    )


def _stage2_prediction(study_id: str, decision: str) -> ScreeningPrediction:
    return ScreeningPrediction(
        example_id=f"csmed_ft::dev::review-1::{study_id}::abstract_plus_full_text",
        decision=decision,
        main_reason=f"Stage 2 says {decision}.",
        metadata={"input_setting": "abstract_plus_full_text"},
    )


def test_stage1_exclude_is_final_and_not_sent_to_stage2() -> None:
    stage1_examples = [_example("study-1", setting=InputSetting.abstract_only)]
    stage2_examples = [_example("study-1", setting=InputSetting.abstract_plus_full_text)]

    artifacts = combine_two_stage_predictions(
        stage1_examples=stage1_examples,
        stage1_predictions=[_stage1_prediction("study-1", "exclude")],
        stage2_examples=stage2_examples,
        stage2_predictions=[_stage2_prediction("study-1", "include")],
        stage2_method="direct_criteria_aware",
        run_id="run-1",
        stage1_examples_path="stage1.examples.jsonl",
        stage1_predictions_path="stage1.predictions.jsonl",
        stage2_examples_path="stage2.examples.jsonl",
        stage2_predictions_path="stage2.predictions.jsonl",
    )

    prediction = artifacts.predictions[0]
    assert prediction.decision == "exclude"
    assert prediction.metadata["stage1_action"] == "auto_exclude"
    assert prediction.metadata["sent_to_full_text"] is False
    assert artifacts.stage2_inputs == []


def test_stage1_include_uses_stage2_prediction_as_final() -> None:
    stage1_examples = [_example("study-1", setting=InputSetting.abstract_only)]
    stage2_examples = [_example("study-1", setting=InputSetting.abstract_plus_full_text)]

    artifacts = combine_two_stage_predictions(
        stage1_examples=stage1_examples,
        stage1_predictions=[_stage1_prediction("study-1", "include")],
        stage2_examples=stage2_examples,
        stage2_predictions=[_stage2_prediction("study-1", "exclude")],
        stage2_method="direct_criteria_aware",
        run_id="run-1",
        stage1_examples_path="stage1.examples.jsonl",
        stage1_predictions_path="stage1.predictions.jsonl",
        stage2_examples_path="stage2.examples.jsonl",
        stage2_predictions_path="stage2.predictions.jsonl",
    )

    prediction = artifacts.predictions[0]
    assert prediction.decision == "exclude"
    assert prediction.main_reason == "Stage 2 says exclude."
    assert prediction.metadata["stage2_decision"] == "exclude"
    assert prediction.metadata["sent_to_full_text"] is True
    assert [example.example_id for example in artifacts.stage2_inputs] == [stage2_examples[0].example_id]


def test_missing_stage2_prediction_is_conservative_include_needs_review() -> None:
    stage1_examples = [_example("study-1", setting=InputSetting.abstract_only)]
    stage2_examples = [_example("study-1", setting=InputSetting.abstract_plus_full_text)]

    artifacts = combine_two_stage_predictions(
        stage1_examples=stage1_examples,
        stage1_predictions=[_stage1_prediction("study-1", "include")],
        stage2_examples=stage2_examples,
        stage2_predictions=[],
        stage2_method="criterion_wise_evidence_grounded",
        run_id="run-1",
        stage1_examples_path="stage1.examples.jsonl",
        stage1_predictions_path="stage1.predictions.jsonl",
        stage2_examples_path="stage2.examples.jsonl",
        stage2_predictions_path="stage2.predictions.jsonl",
    )

    prediction = artifacts.predictions[0]
    assert prediction.decision == "include"
    assert prediction.metadata["needs_review"] is True
    assert prediction.metadata["needs_review_reason"] == "missing_stage2_prediction"
    assert artifacts.missing_stage2_predictions[0]["stage2_example_id"] == stage2_examples[0].example_id


def test_missing_stage1_prediction_is_conservative_include_needs_review() -> None:
    stage1_examples = [_example("study-1", setting=InputSetting.abstract_only)]
    stage2_examples = [_example("study-1", setting=InputSetting.abstract_plus_full_text)]

    artifacts = combine_two_stage_predictions(
        stage1_examples=stage1_examples,
        stage1_predictions=[],
        stage2_examples=stage2_examples,
        stage2_predictions=[_stage2_prediction("study-1", "exclude")],
        stage2_method="direct_criteria_aware",
        run_id="run-1",
        stage1_examples_path="stage1.examples.jsonl",
        stage1_predictions_path="stage1.predictions.jsonl",
        stage2_examples_path="stage2.examples.jsonl",
        stage2_predictions_path="stage2.predictions.jsonl",
    )

    prediction = artifacts.predictions[0]
    assert prediction.decision == "include"
    assert prediction.metadata["stage1_action"] == "needs_review_missing_stage1_prediction"
    assert prediction.metadata["sent_to_full_text"] is False
    assert prediction.metadata["needs_review_reason"] == "missing_stage1_prediction"
    assert artifacts.stage2_inputs == []


def test_sent_to_full_text_drives_workload_flags() -> None:
    stage1_examples = [
        _example("study-1", setting=InputSetting.abstract_only),
        _example("study-2", setting=InputSetting.abstract_only),
    ]
    stage2_examples = [
        _example("study-1", setting=InputSetting.abstract_plus_full_text),
        _example("study-2", setting=InputSetting.abstract_plus_full_text),
    ]

    artifacts = combine_two_stage_predictions(
        stage1_examples=stage1_examples,
        stage1_predictions=[
            _stage1_prediction("study-1", "include"),
            _stage1_prediction("study-2", "exclude"),
        ],
        stage2_examples=stage2_examples,
        stage2_predictions=[_stage2_prediction("study-1", "include")],
        stage2_method="direct_criteria_aware",
        run_id="run-1",
        stage1_examples_path="stage1.examples.jsonl",
        stage1_predictions_path="stage1.predictions.jsonl",
        stage2_examples_path="stage2.examples.jsonl",
        stage2_predictions_path="stage2.predictions.jsonl",
    )

    assert [prediction.metadata["sent_to_full_text"] for prediction in artifacts.predictions] == [
        True,
        False,
    ]


def test_duplicate_prediction_ids_raise_clear_error() -> None:
    stage1_examples = [_example("study-1", setting=InputSetting.abstract_only)]
    stage2_examples = [_example("study-1", setting=InputSetting.abstract_plus_full_text)]
    duplicated = [_stage1_prediction("study-1", "include"), _stage1_prediction("study-1", "exclude")]

    with pytest.raises(ValueError, match="duplicate stage1 prediction example_id"):
        combine_two_stage_predictions(
            stage1_examples=stage1_examples,
            stage1_predictions=duplicated,
            stage2_examples=stage2_examples,
            stage2_predictions=[],
            stage2_method="direct_criteria_aware",
            run_id="run-1",
            stage1_examples_path="stage1.examples.jsonl",
            stage1_predictions_path="stage1.predictions.jsonl",
            stage2_examples_path="stage2.examples.jsonl",
            stage2_predictions_path="stage2.predictions.jsonl",
        )


def test_stage2_without_matching_stage1_example_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="stage2 examples without matching stage1 examples"):
        combine_two_stage_predictions(
            stage1_examples=[_example("study-1", setting=InputSetting.abstract_only)],
            stage1_predictions=[],
            stage2_examples=[_example("study-2", setting=InputSetting.abstract_plus_full_text)],
            stage2_predictions=[],
            stage2_method="direct_criteria_aware",
            run_id="run-1",
            stage1_examples_path="stage1.examples.jsonl",
            stage1_predictions_path="stage1.predictions.jsonl",
            stage2_examples_path="stage2.examples.jsonl",
            stage2_predictions_path="stage2.predictions.jsonl",
        )


def test_cli_smoke_generates_key_outputs(tmp_path) -> None:
    stage1_examples_path = tmp_path / "stage1.examples.jsonl"
    stage1_predictions_path = tmp_path / "stage1.predictions.jsonl"
    stage2_examples_path = tmp_path / "stage2.examples.jsonl"
    stage2_predictions_path = tmp_path / "stage2.predictions.jsonl"
    reference_metrics_path = tmp_path / "reference.metrics.json"
    output_dir = tmp_path / "two-stage"

    stage1_examples = [
        _example("study-1", setting=InputSetting.abstract_only, gold_decision="include"),
        _example("study-2", setting=InputSetting.abstract_only, gold_decision="exclude"),
    ]
    stage2_examples = [
        _example("study-1", setting=InputSetting.abstract_plus_full_text, gold_decision="include"),
        _example("study-2", setting=InputSetting.abstract_plus_full_text, gold_decision="exclude"),
    ]
    write_model_jsonl(stage1_examples_path, stage1_examples)
    write_model_jsonl(
        stage1_predictions_path,
        [_stage1_prediction("study-1", "include"), _stage1_prediction("study-2", "exclude")],
    )
    write_model_jsonl(stage2_examples_path, stage2_examples)
    write_model_jsonl(stage2_predictions_path, [_stage2_prediction("study-1", "include")])
    reference_metrics_path.write_text(
        """
{
  "counts": {"tp": 1, "tn": 1, "fp": 0, "fn": 0, "total": 2},
  "decision_metrics": {
    "sensitivity": 1.0,
    "specificity": 1.0,
    "precision": 1.0,
    "balanced_accuracy": 1.0,
    "macro_f1": 1.0,
    "false_negative_count": 0
  },
  "workload_metrics": {"full_text_workload": 1.0, "full_text_workload_reduction": 0.0},
  "metadata": {
    "run_id": "reference-run",
    "method": "direct_criteria_aware",
    "benchmark": "csmed_ft",
    "split": "dev",
    "input_setting": "abstract_plus_full_text",
    "predictions_path": "reference.predictions.jsonl"
  }
}
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "screening.cli.run_two_stage",
            "--stage1-examples",
            str(stage1_examples_path),
            "--stage1-predictions",
            str(stage1_predictions_path),
            "--stage2-examples",
            str(stage2_examples_path),
            "--stage2-predictions",
            str(stage2_predictions_path),
            "--stage2-method",
            "direct_criteria_aware",
            "--run-id",
            "two-stage-smoke",
            "--output-dir",
            str(output_dir),
            "--reference-metrics",
            str(reference_metrics_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    for filename in [
        "predictions.jsonl",
        "stage1_actions.jsonl",
        "stage2_inputs.jsonl",
        "missing_stage2_predictions.jsonl",
        "run_metadata.json",
    ]:
        assert (output_dir / filename).exists()
    metrics_path = (
        "results/metrics/csmed_ft/dev/two_stage/two-stage-smoke.json"
    )
    assert metrics_path in result.stdout
    assert read_jsonl(output_dir / "stage2_inputs.jsonl")[0]["study_id"] == "study-1"
    metadata = read_json(output_dir / "run_metadata.json")
    assert metadata["metadata"]["stage2_input_count"] == 1

    comparison_path = Path("results/tables/one_step_vs_two_stage.csv")
    if comparison_path.exists():
        rows = read_jsonl(output_dir / "predictions.jsonl")
        assert len(rows) == 2
        lines = comparison_path.read_text(encoding="utf-8").splitlines()
        filtered = [
            line
            for line in lines
            if "two-stage-smoke" not in line and "reference-run" not in line
        ]
        comparison_path.write_text("\n".join(filtered) + ("\n" if filtered else ""), encoding="utf-8")
    generated_metrics = Path("results/metrics/csmed_ft/dev/two_stage/two-stage-smoke.json")
    if generated_metrics.exists():
        generated_metrics.unlink()
    for csv_path in [
        Path("results/tables/run_index.csv"),
        Path("results/tables/automation_readiness.csv"),
    ]:
        if csv_path.exists():
            lines = csv_path.read_text(encoding="utf-8").splitlines()
            filtered = [line for line in lines if "two-stage-smoke" not in line]
            csv_path.write_text(
                "\n".join(filtered) + ("\n" if filtered else ""),
                encoding="utf-8",
            )
