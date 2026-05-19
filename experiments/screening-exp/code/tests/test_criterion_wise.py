from __future__ import annotations

import csv
import json
from pathlib import Path

from screening.cli import run_criterion_wise
from screening.io_utils import read_json, read_jsonl, read_prediction_jsonl, write_model_jsonl
from screening.pipeline.aggregation import (
    aggregate_csmed_criterion_judgments,
    apply_aggregation_to_prediction,
)
from screening.prompts.criterion_wise import build_criterion_wise_prompt
from screening.schemas import Decision, InputSetting, ScreeningExample, ScreeningPrediction, TextSection


def _example(*, setting: InputSetting, with_raw_criteria: bool = True) -> ScreeningExample:
    raw_criteria = {
        "criteria": {
            "Types of participants": "Adults with chronic kidney disease.",
            "Types of studies": "Randomized trials.",
        },
        "criteria_text": "Protocol-only publications were excluded.",
    }
    return ScreeningExample(
        example_id=f"example-{setting.value}",
        benchmark="csmed_ft",
        split="test-small",
        review_id="review-1",
        study_id="study-1",
        question="Adults with chronic kidney disease receiving telehealth follow-up.",
        title="Telehealth follow-up for adults with CKD",
        abstract="Randomized trial in adults with chronic kidney disease using remote follow-up.",
        full_text_sections=[
            TextSection(
                title="Methods",
                section_id="methods",
                source="full_text_sections",
                text="Randomized trial in adults with chronic kidney disease receiving telehealth follow-up.",
            ),
            TextSection(
                title="Publication type",
                section_id="publication_type",
                source="full_text_sections",
                text="This is a completed randomized trial report rather than a protocol.",
            ),
        ],
        criteria={
            "inclusion": ["Adults with chronic kidney disease", "Randomized trials"],
            "exclusion": ["Protocol-only publications"],
            "raw": raw_criteria if with_raw_criteria else {},
        },
        input_setting=setting,
        gold_decision="include",
    )


def _write_provider_and_defaults(tmp_path: Path) -> tuple[Path, Path]:
    provider_path = tmp_path / "providers.yaml"
    defaults_path = tmp_path / "defaults.yaml"
    provider_path.write_text(
        "\n".join(
            [
                "providers:",
                "  - provider: openai",
                "    model: gpt-test",
                "    api_key_env: OPENAI_API_KEY",
                "    timeout_seconds: 30",
                "    temperature: 0.0",
                "    max_tokens: 500",
                "    max_retries: 1",
                "    retry_backoff_seconds: 0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    defaults_path.write_text(
        "\n".join(
            [
                "default_provider: openai",
                "prompt_version: v3",
                "output_root: results",
                "high_confidence_threshold: 0.8",
                "default_temperature: 0.0",
                "default_max_tokens: 500",
                "default_max_retries: 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return provider_path, defaults_path


class _MockClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> tuple[str, str | None]:
        self.calls.append(prompt)
        marker = "Example ID:\n"
        start = prompt.index(marker) + len(marker)
        end = prompt.find("\n", start)
        example_id = prompt[start:end].strip()
        return self.responses[example_id], f"req-{example_id}"


def test_build_criterion_wise_prompt_uses_raw_criteria_and_candidate_text() -> None:
    prompt, metadata = build_criterion_wise_prompt(
        _example(setting=InputSetting.full_text_only),
        setting=InputSetting.full_text_only,
        prompt_version="v3",
    )

    assert "Raw review criteria:" in prompt
    assert "Review criteria section:" in prompt
    assert "Criteria text fallback:" in prompt
    assert "Candidate study:" in prompt
    assert "Title: Telehealth follow-up for adults with CKD" in prompt
    assert "Abstract: Randomized trial in adults with chronic kidney disease using remote follow-up." in prompt
    assert '"text": "Adults with chronic kidney disease"' in prompt
    assert '"judgment": "unclear"' in prompt
    assert '"reason"' not in prompt
    assert '"evidence_spans"' not in prompt
    assert metadata["text_source"] == "full_text_sections"
    assert metadata["criteria_source"] == "criteria_plus_criteria_text"


def test_build_criterion_wise_prompt_falls_back_to_question_when_raw_criteria_missing() -> None:
    prompt, metadata = build_criterion_wise_prompt(
        _example(setting=InputSetting.full_text_only, with_raw_criteria=False),
        setting=InputSetting.full_text_only,
        prompt_version="v3",
    )

    assert "No explicit review criteria were available" in prompt
    assert "Adults with chronic kidney disease receiving telehealth follow-up." in prompt
    assert metadata["criteria_source"] == "question_fallback"


def test_build_criterion_wise_prompt_fixed_specs_uses_stable_criteria_ids() -> None:
    prompt, metadata = build_criterion_wise_prompt(
        _example(setting=InputSetting.abstract_plus_full_text),
        setting=InputSetting.abstract_plus_full_text,
        prompt_version="fixed_v1",
        criteria_mode="fixed_specs",
    )

    assert "Fixed review criteria:" in prompt
    assert "- inc_1: Adults with chronic kidney disease" in prompt
    assert "- inc_2: Randomized trials" in prompt
    assert "- exc_1: Protocol-only publications" in prompt
    assert "Raw review criteria context:" not in prompt
    assert metadata["criteria_mode"] == "fixed_specs"
    assert metadata["fixed_criteria_source"] == "review_clauses"
    assert metadata["expected_criterion_ids"] == "inc_1,inc_2,exc_1"


def test_build_criterion_wise_prompt_hybrid_specs_keeps_raw_context() -> None:
    prompt, metadata = build_criterion_wise_prompt(
        _example(setting=InputSetting.abstract_plus_full_text),
        setting=InputSetting.abstract_plus_full_text,
        prompt_version="hybrid_v1",
        criteria_mode="hybrid_specs_raw",
    )

    assert "Raw review criteria context:" in prompt
    assert "Review criteria section:" in prompt
    assert "Fixed review criteria to judge:" in prompt
    assert "- inc_1: Adults with chronic kidney disease" in prompt
    assert metadata["criteria_mode"] == "hybrid_specs_raw"
    assert metadata["expected_criterion_ids"] == "inc_1,inc_2,exc_1"


def test_aggregation_uses_inc_exc_prefix_rules() -> None:
    prediction = ScreeningPrediction(
        example_id="example-1",
        decision=Decision.include,
        criterion_judgments={
            "inc_1": {"text": "Adults with chronic kidney disease", "judgment": "yes"},
            "inc_2": {"text": "Randomized trials", "judgment": "unclear"},
            "exc_1": {"text": "Protocol-only publications", "judgment": "no"},
        },
    )

    aggregation = aggregate_csmed_criterion_judgments(prediction, [])
    finalized = apply_aggregation_to_prediction(prediction, aggregation)

    assert aggregation.final_decision == Decision.include
    assert aggregation.aggregation_status == "needs_review"
    assert finalized.metadata["aggregation_status"] == "needs_review"

    prediction.criterion_judgments["exc_1"].judgment = "yes"
    aggregation = aggregate_csmed_criterion_judgments(prediction, [])
    assert aggregation.final_decision == Decision.exclude
    assert aggregation.failed_criterion == "exc_1"

    prediction.criterion_judgments["exc_1"].judgment = "no"
    prediction.criterion_judgments["inc_2"].judgment = "no"
    aggregation = aggregate_csmed_criterion_judgments(prediction, [])
    assert aggregation.final_decision == Decision.exclude
    assert aggregation.failed_criterion == "inc_2"


def test_run_criterion_wise_end_to_end_with_mock_client(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "preds"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    example1 = _example(setting=InputSetting.full_text_only)
    example2 = _example(setting=InputSetting.full_text_only).model_copy(
        update={"example_id": "example-second", "study_id": "study-2"}
    )
    write_model_jsonl(examples_path, [example1, example2])

    mock_client = _MockClient(
        {
            example1.example_id: json.dumps(
                {
                    "criterion_judgments": {
                        "inc_1": {
                            "text": "Adults with chronic kidney disease",
                            "judgment": "yes",
                        },
                        "inc_2": {
                            "text": "Randomized trials",
                            "judgment": "yes",
                        },
                        "exc_1": {
                            "text": "Protocol-only publications",
                            "judgment": "no",
                        },
                    }
                }
            ),
            example2.example_id: "not json",
        }
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(run_criterion_wise, "_build_client", lambda **_: mock_client)

    exit_code = run_criterion_wise.main(
        [
            "--examples",
            str(examples_path),
            "--provider-config",
            str(provider_path),
            "--defaults-config",
            str(defaults_path),
            "--input-setting",
            "full_text_only",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "criterion-run",
            "--workers",
            "2",
            "--top-k",
            "2",
        ]
    )

    assert exit_code == 0
    predictions = read_prediction_jsonl(output_dir / "predictions.jsonl")
    errors = read_jsonl(output_dir / "errors.jsonl")
    evaluation_examples = read_jsonl(output_dir / "evaluation_examples.jsonl")
    assert len(predictions) == 1
    assert predictions[0].decision == Decision.include
    assert predictions[0].metadata["prediction_schema"] == "criterion_wise_minimal_v1"
    assert predictions[0].metadata["aggregation_status"] == "include_clear"
    assert predictions[0].criterion_judgments["inc_1"].text == "Adults with chronic kidney disease"
    assert len(errors) == 1
    assert errors[0]["example_id"] == example2.example_id
    assert errors[0]["error_type"] == "prediction_validation_error"
    assert len(evaluation_examples) == 1
    assert not (output_dir / "selected_evidence.jsonl").exists()

    metadata_path = (
        run_criterion_wise.results_root
        / "logs"
        / "csmed_ft"
        / "test-small"
        / "criterion_wise_evidence_grounded"
        / "criterion-run"
        / "run_metadata.json"
    )
    metrics_path = (
        run_criterion_wise.results_root
        / "metrics"
        / "csmed_ft"
        / "test-small"
        / "criterion_wise_evidence_grounded"
        / "criterion-run.json"
    )
    metadata = read_json(metadata_path)
    metrics = read_json(metrics_path)
    assert metadata["prompt_version"] == "v3"
    assert metadata["metadata"]["criteria_input_mode"] == "raw"
    assert metadata["metadata"]["criteria_probe_limit"] == 2
    assert metadata["metadata"]["aggregation_policy"] == "conservative_binary_with_needs_review_flag"
    assert metrics["metadata"]["run_id"] == "criterion-run"

    run_index_path = run_criterion_wise.results_root / "tables" / "run_index.csv"
    with run_index_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["run_id"] == "criterion-run" for row in rows)


def test_run_criterion_wise_resume_skips_completed_example(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "preds"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    example = _example(setting=InputSetting.full_text_only)
    write_model_jsonl(examples_path, [example])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_model_jsonl(
        output_dir / "predictions.jsonl",
        [
            ScreeningPrediction(
                example_id=example.example_id,
                decision=Decision.include,
                main_reason="Existing prediction.",
                metadata={"prediction_schema": "criterion_wise_minimal_v1"},
            )
        ],
    )

    class _FailingClient:
        def invoke(self, prompt: str) -> tuple[str, str | None]:
            raise AssertionError("client should not be called when --resume skips the example")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(run_criterion_wise, "_build_client", lambda **_: _FailingClient())

    exit_code = run_criterion_wise.main(
        [
            "--examples",
            str(examples_path),
            "--provider-config",
            str(provider_path),
            "--defaults-config",
            str(defaults_path),
            "--input-setting",
            "full_text_only",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "criterion-resume",
            "--resume",
        ]
    )

    assert exit_code == 0
    predictions = read_prediction_jsonl(output_dir / "predictions.jsonl")
    assert len(predictions) == 1


def test_run_criterion_wise_fixed_specs_rejects_missing_expected_id(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples-fixed.jsonl"
    output_dir = tmp_path / "preds-fixed"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    example = _example(setting=InputSetting.abstract_plus_full_text)
    write_model_jsonl(examples_path, [example])

    mock_client = _MockClient(
        {
            example.example_id: json.dumps(
                {
                    "criterion_judgments": {
                        "inc_1": {
                            "text": "Adults with chronic kidney disease",
                            "judgment": "yes",
                        },
                        "exc_1": {
                            "text": "Protocol-only publications",
                            "judgment": "no",
                        },
                    }
                }
            )
        }
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(run_criterion_wise, "_build_client", lambda **_: mock_client)

    exit_code = run_criterion_wise.main(
        [
            "--examples",
            str(examples_path),
            "--provider-config",
            str(provider_path),
            "--defaults-config",
            str(defaults_path),
            "--input-setting",
            "abstract_plus_full_text",
            "--prompt-version",
            "fixed_v1",
            "--criteria-mode",
            "fixed_specs",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "criterion-fixed-missing",
        ]
    )

    assert exit_code == 0
    assert not (output_dir / "predictions.jsonl").exists()
    errors = read_jsonl(output_dir / "errors.jsonl")
    assert len(errors) == 1
    assert errors[0]["error_type"] == "prediction_validation_error"
    assert "missing criterion ids: inc_2" in errors[0]["validation_errors"]
    assert errors[0]["metadata"]["criteria_input_mode"] == "fixed_specs"
