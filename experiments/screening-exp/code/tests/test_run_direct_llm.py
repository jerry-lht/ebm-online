from __future__ import annotations

import csv
import json
from pathlib import Path

from screening.cli import run_direct_llm
from screening.io_utils import (
    read_json,
    read_jsonl,
    read_model_jsonl,
    read_prediction_jsonl,
    write_model_jsonl,
)
from screening.schemas import InputSetting, ScreeningExample, TextSection


def _example(example_id: str) -> ScreeningExample:
    return ScreeningExample(
        example_id=example_id,
        benchmark="csmed_ft",
        split="test-small",
        review_id="review-1",
        study_id=example_id,
        title=f"Title for {example_id}",
        abstract=f"Abstract for {example_id}",
        full_text_sections=[TextSection(title="Methods", text="Methods text.")],
        input_setting=InputSetting.abstract_only,
        gold_decision="include" if example_id.endswith("1") else "exclude",
    )


def _full_text_example(example_id: str) -> ScreeningExample:
    return ScreeningExample(
        example_id=example_id,
        benchmark="csmed_ft",
        split="test-small",
        review_id="review-1",
        study_id=example_id,
        title=f"Title for {example_id}",
        abstract=f"Abstract for {example_id}",
        full_text_sections=[TextSection(title="Methods", text="Methods text.")],
        input_setting=InputSetting.full_text_only,
        gold_decision="include",
    )


class _MockClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> tuple[str, str | None]:
        self.calls.append(prompt)
        title_marker = "Title: "
        if title_marker in prompt:
            start = prompt.index(title_marker) + len(title_marker)
            end = prompt.find("\n", start)
            title = prompt[start:end].strip()
            example_id = title.replace("Title for ", "")
        elif len(self.responses) == 1:
            example_id = next(iter(self.responses))
        else:
            example_id = "example-1"
        return self.responses[example_id], f"req-{example_id}"


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
                "prompt_version: v0",
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


def test_run_direct_llm_end_to_end_with_mock_client(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "preds"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    write_model_jsonl(examples_path, [_example("example-1"), _example("example-2")])

    mock_client = _MockClient(
        {
            "example-1": json.dumps(
                {
                    "decision": "include",
                    "criterion_judgments": {
                        "population": {
                            "judgment": "yes",
                            "reason": "Matches population.",
                            "evidence_spans": [{"text": "Adults with CKD"}],
                        },
                        "intervention": {
                            "judgment": "yes",
                            "reason": "Matches intervention.",
                            "evidence_spans": [{"text": "Intervention described"}],
                        },
                        "comparator": {
                            "judgment": "not_applicable",
                            "reason": "Comparator not required.",
                            "evidence_spans": [{"text": "Single-arm trial"}],
                        },
                        "outcome": {
                            "judgment": "yes",
                            "reason": "Outcome matches.",
                            "evidence_spans": [{"text": "Kidney outcome"}],
                        },
                        "study_design": {
                            "judgment": "yes",
                            "reason": "Randomized trial.",
                            "evidence_spans": [{"text": "Randomized"}],
                        },
                    },
                    "failed_criterion": None,
                    "main_reason": "Eligible study.",
                    "evidence_spans": [{"text": "Adults with CKD"}],
                }
            ),
            "example-2": "not json",
        }
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(run_direct_llm, "_build_client", lambda **_: mock_client)

    exit_code = run_direct_llm.main(
        [
            "--examples",
            str(examples_path),
            "--provider-config",
            str(provider_path),
            "--defaults-config",
            str(defaults_path),
            "--input-setting",
            "abstract_only",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "run-test",
            "--workers",
            "2",
        ]
    )

    assert exit_code == 0
    predictions_path = output_dir / "predictions.jsonl"
    errors_path = output_dir / "errors.jsonl"
    evaluation_examples_path = output_dir / "evaluation_examples.jsonl"
    predictions = read_model_jsonl(predictions_path, run_direct_llm.ScreeningPrediction)
    errors = read_jsonl(errors_path)
    evaluation_examples = read_jsonl(evaluation_examples_path)
    assert len(predictions) == 1
    assert predictions[0].example_id == "example-1"
    assert len(errors) == 1
    assert errors[0]["example_id"] == "example-2"
    assert errors[0]["error_type"] == "prediction_validation_error"
    assert len(evaluation_examples) == 1

    metadata_path = (
        run_direct_llm.results_root
        / "logs"
        / "csmed_ft"
        / "test-small"
        / "direct_criteria_aware"
        / "run-test"
        / "run_metadata.json"
    )
    metrics_path = (
        run_direct_llm.results_root
        / "metrics"
        / "csmed_ft"
        / "test-small"
        / "direct_criteria_aware"
        / "run-test.json"
    )
    run_index_path = run_direct_llm.results_root / "tables" / "run_index.csv"
    metadata = read_json(metadata_path)
    metrics = read_json(metrics_path)
    assert metadata["success_count"] == 1
    assert metadata["error_count"] == 1
    assert metadata["prompt_version"] == "v0"
    assert metadata["metadata"]["workers"] == 2
    assert metrics["metadata"]["run_id"] == "run-test"
    with run_index_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["run_id"] == "run-test" for row in rows)


def test_run_direct_llm_abstract_v3_uses_minimal_schema(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples-v3.jsonl"
    output_dir = tmp_path / "preds-v3"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    write_model_jsonl(examples_path, [_example("example-1")])

    mock_client = _MockClient(
        {
            "example-1": json.dumps(
                {
                    "decision": "include",
                    "main_reason": "Abstract remains plausibly relevant to the review topic.",
                }
            )
        }
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(run_direct_llm, "_build_client", lambda **_: mock_client)

    exit_code = run_direct_llm.main(
        [
            "--examples",
            str(examples_path),
            "--provider-config",
            str(provider_path),
            "--defaults-config",
            str(defaults_path),
            "--input-setting",
            "abstract_only",
            "--prompt-version",
            "v3",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "run-v3",
        ]
    )

    assert exit_code == 0
    predictions = read_prediction_jsonl(output_dir / "predictions.jsonl")
    assert len(predictions) == 1
    assert isinstance(predictions[0], run_direct_llm.AbstractScreeningPrediction)
    assert predictions[0].metadata["prediction_schema"] == "abstract_only_v3"
    assert mock_client.calls[0].splitlines()[0] == "Task:"

    metadata = read_json(
        run_direct_llm.results_root
        / "logs"
        / "csmed_ft"
        / "test-small"
        / "direct_criteria_aware"
        / "run-v3"
        / "run_metadata.json"
    )
    assert metadata["prompt_version"] == "v3"
    assert metadata["metadata"]["prediction_schema"] == "abstract_only_v3"


def test_run_direct_llm_full_text_only_keeps_rich_schema(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples-full-text.jsonl"
    output_dir = tmp_path / "preds-full-text"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    write_model_jsonl(examples_path, [_full_text_example("example-ft-1")])

    mock_client = _MockClient(
        {
            "example-ft-1": json.dumps(
                {
                    "decision": "include",
                    "criterion_judgments": {
                        "population": {
                            "judgment": "yes",
                            "reason": "Population matches.",
                            "evidence_spans": [{"text": "Adults with CKD"}],
                        }
                    },
                    "failed_criterion": None,
                    "main_reason": "Full text supports inclusion.",
                    "evidence_spans": [{"text": "Adults with CKD"}],
                }
            )
        }
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(run_direct_llm, "_build_client", lambda **_: mock_client)

    exit_code = run_direct_llm.main(
        [
            "--examples",
            str(examples_path),
            "--provider-config",
            str(provider_path),
            "--defaults-config",
            str(defaults_path),
            "--input-setting",
            "full_text_only",
            "--prompt-version",
            "v0",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "run-full-text",
        ]
    )

    assert exit_code == 0
    predictions = read_prediction_jsonl(output_dir / "predictions.jsonl")
    assert len(predictions) == 1
    assert isinstance(predictions[0], run_direct_llm.ScreeningPrediction)
    assert predictions[0].metadata["prediction_schema"] == "screening_prediction_v0"


def test_run_direct_llm_resume_skips_processed_ids(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "preds"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    write_model_jsonl(examples_path, [_example("example-1"), _example("example-2")])

    output_dir.mkdir(parents=True, exist_ok=True)
    write_model_jsonl(
        output_dir / "predictions.jsonl",
        [
            run_direct_llm.ScreeningPrediction(
                example_id="example-1",
                decision="include",
            )
        ],
    )

    mock_client = _MockClient(
        {
            "example-2": json.dumps(
                {
                    "decision": "exclude",
                    "criterion_judgments": {},
                    "failed_criterion": "population",
                    "main_reason": "Wrong population.",
                    "evidence_spans": [{"text": "Different population"}],
                }
            )
        }
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(run_direct_llm, "_build_client", lambda **_: mock_client)

    exit_code = run_direct_llm.main(
        [
            "--examples",
            str(examples_path),
            "--provider-config",
            str(provider_path),
            "--defaults-config",
            str(defaults_path),
            "--input-setting",
            "abstract_only",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "run-resume",
            "--resume",
        ]
    )

    assert exit_code == 0
    predictions = read_jsonl(output_dir / "predictions.jsonl")
    assert len(predictions) == 2
    assert len(mock_client.calls) == 1


def test_run_direct_llm_rejects_non_positive_workers(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    write_model_jsonl(examples_path, [_example("example-1")])

    try:
        run_direct_llm.main(
            [
                "--examples",
                str(examples_path),
                "--provider-config",
                str(provider_path),
                "--defaults-config",
                str(defaults_path),
                "--input-setting",
                "abstract_only",
                "--workers",
                "0",
            ]
        )
    except ValueError as exc:
        assert "--workers must be positive" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-positive workers")


def test_run_direct_llm_rejects_existing_run_lock(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "preds"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    write_model_jsonl(examples_path, [_example("example-1")])

    log_dir = (
        run_direct_llm.results_root
        / "logs"
        / "csmed_ft"
        / "test-small"
        / "direct_criteria_aware"
        / "run-lock"
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / ".run.lock").write_text("locked\n", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        run_direct_llm,
        "_build_client",
        lambda **_: _MockClient({"example-1": json.dumps({"decision": "include", "criterion_judgments": {}, "failed_criterion": None, "main_reason": "ok", "evidence_spans": []})}),
    )

    try:
        run_direct_llm.main(
            [
                "--examples",
                str(examples_path),
                "--provider-config",
                str(provider_path),
                "--defaults-config",
                str(defaults_path),
                "--input-setting",
                "abstract_only",
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-lock",
            ]
        )
    except run_direct_llm.RunLockError as exc:
        assert "run lock already exists" in str(exc)
    else:
        raise AssertionError("expected RunLockError when lock file already exists")


def test_run_direct_llm_rejects_duplicate_predictions_before_evaluation(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "preds"
    provider_path, defaults_path = _write_provider_and_defaults(tmp_path)
    write_model_jsonl(examples_path, [_example("example-1")])

    output_dir.mkdir(parents=True, exist_ok=True)
    write_model_jsonl(
        output_dir / "predictions.jsonl",
        [
            run_direct_llm.ScreeningPrediction(example_id="example-1", decision="include"),
            run_direct_llm.ScreeningPrediction(example_id="example-1", decision="exclude"),
        ],
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        run_direct_llm,
        "_build_client",
        lambda **_: _MockClient({}),
    )

    try:
        run_direct_llm.main(
            [
                "--examples",
                str(examples_path),
                "--provider-config",
                str(provider_path),
                "--defaults-config",
                str(defaults_path),
                "--input-setting",
                "abstract_only",
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-dup-check",
                "--resume",
            ]
        )
    except run_direct_llm.ResultConflictError as exc:
        assert "duplicate predictions detected" in str(exc) or "conflicting duplicate predictions detected" in str(exc)
    else:
        raise AssertionError("expected ResultConflictError for duplicate predictions")
