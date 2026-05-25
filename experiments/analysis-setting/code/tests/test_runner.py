from __future__ import annotations

import json
from pathlib import Path

from analysis_setting_experiment.cli import command_recanonicalize
from analysis_setting_experiment.io_utils import dump_json, dump_jsonl, load_json
from analysis_setting_experiment.runner import RunConfig, build_backend, run_split


def _dataset_row(review_id: str) -> dict[str, object]:
    return {
        "review_id": review_id,
        "sr_title": "Review",
        "sr_pico": {"outcome": ["Outcome A"]},
        "studies": [{"title": "Study", "abstract": "Text"}],
        "metadata": {
            "coverage_level": "HIGH",
            "abstract_study_count_bucket": "0-3",
            "gold_candidate_count_bucket": "1-10",
        },
        "gold_partial_analysis_settings": [],
    }


def test_run_split_supports_resume_and_rerun_flags(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dev.jsonl"
    dump_jsonl(dataset_path, [_dataset_row("R1")])
    config = RunConfig(
        model_name="mock-model",
        model_version="v1",
        split="dev",
        output_dir=tmp_path,
        concurrency=1,
    )
    backend = build_backend("mock")
    run_split(dataset_path, config, backend)
    state_path = tmp_path / "runs" / "mock-model" / "dev" / "R1" / "state.json"
    state = load_json(state_path)
    assert state["status"] == "success"
    first_attempt_count = state["attempt_count"]
    run_split(dataset_path, config, backend)
    state = load_json(state_path)
    assert state["attempt_count"] == first_attempt_count


def test_json_file_backend_and_invalid_output_rerun(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dev.jsonl"
    dump_jsonl(dataset_path, [_dataset_row("R1")])
    source_path = tmp_path / "predictions.json"
    source_path.write_text(json.dumps({"R1": "not-json"}), encoding="utf-8")
    config = RunConfig(
        model_name="file-model",
        model_version="v1",
        split="dev",
        output_dir=tmp_path,
        concurrency=1,
    )
    backend = build_backend("json_file", json_source=source_path)
    run_split(dataset_path, config, backend)
    state_path = tmp_path / "runs" / "file-model" / "dev" / "R1" / "state.json"
    state = load_json(state_path)
    assert state["status"] == "invalid_output"
    source_path.write_text(
        json.dumps(
            {
                "R1": [
                    {
                        "outcome_concept": "Outcome A",
                        "data_type": "",
                        "candidate_effect_measure": "",
                        "comparisons": [],
                        "arm_pairs": [],
                        "subgroup_candidates": [],
                        "timepoints": [],
                        "reported_outcome_measures": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rerun_config = RunConfig(
        model_name="file-model",
        model_version="v1",
        split="dev",
        output_dir=tmp_path,
        concurrency=1,
        rerun_invalid_output=True,
    )
    run_split(dataset_path, rerun_config, build_backend("json_file", json_source=source_path))
    state = load_json(state_path)
    assert state["status"] == "success"
    assert state["attempt_count"] == 2


def test_recanonicalize_updates_existing_prediction(tmp_path: Path, capsys: object) -> None:
    dataset_path = tmp_path / "dev.jsonl"
    review = {
        "review_id": "CD015422",
        "sr_title": "Topical repellents for malaria prevention",
        "sr_pico": {"comparison": ["Placebo"], "intervention": ["Mosquito Repellent"]},
        "studies": [{"title": "Study", "abstract": "Text"}],
        "metadata": {
            "coverage_level": "HIGH",
            "abstract_study_count_bucket": "0-3",
            "gold_candidate_count_bucket": "1-10",
        },
        "gold_partial_analysis_settings": [],
    }
    dump_jsonl(dataset_path, [review])
    prediction_path = tmp_path / "runs" / "demo-model" / "dev" / "CD015422" / "latest_prediction.json"
    dump_json(
        prediction_path,
        {
            "review_id": "CD015422",
            "parsed_prediction_json": [
                {
                    "outcome_concept": "malaria episodes",
                    "data_type": "count",
                    "candidate_effect_measure": "incidence rate ratio",
                    "comparisons": ["mosquito repellent vs placebo"],
                    "arm_pairs": [{"experimental_arm": "mosquito repellent", "control_arm": "placebo"}],
                    "subgroup_candidates": [],
                    "timepoints": [],
                    "reported_outcome_measures": ["episodes of malaria", "parasitemia"],
                }
            ],
            "parse_status": "success",
            "schema_valid": True,
        },
    )

    class Args:
        def __init__(self, dataset_path: Path, output_dir: Path) -> None:
            self.dataset_path = str(dataset_path)
            self.output_dir = str(output_dir)
            self.model_name = "demo-model"
            self.split = "dev"
            self.review_id = None

    command_recanonicalize(Args(dataset_path, tmp_path))
    updated = load_json(prediction_path)
    assert updated["canonicalization_version"] == "review_level_v3"
    assert updated["raw_parsed_prediction_json"][0]["outcome_concept"] == "malaria episodes"
    assert updated["canonicalized_prediction_json"][0]["outcome_concept"] == "Malaria prevalence"
    assert updated["parsed_prediction_json"][0]["outcome_concept"] == "Malaria prevalence"
    assert updated["canonicalization_provenance"]["applied_rule_type"] == "review_family"
    captured = capsys.readouterr()
    assert "updated_review_count" in captured.out
