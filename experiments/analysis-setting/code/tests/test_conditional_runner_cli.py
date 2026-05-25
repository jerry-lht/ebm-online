from __future__ import annotations

import json
from pathlib import Path

from analysis_setting_experiment.cli import (
    command_evaluate_conditional,
    command_make_conditional_subset,
    command_prepare_conditional,
    command_run_conditional,
)
from analysis_setting_experiment.io_utils import load_json, load_jsonl
from analysis_setting_experiment.runner import _load_local_api_config



def _benchmark_review() -> dict[str, object]:
    return {
        "review_id": "R1",
        "sr_title": "Review",
        "sr_pico": {"outcome": ["Smoking cessation"]},
        "included_studies": [
            {
                "study_id": "S1",
                "study_year": "2001",
                "primary_report": {"title": "Study 1"},
                "evidence_tier": "full_text",
                "full_content": {
                    "sections": [
                        {"section": "Methods", "text": "Questionnaire and standardized scale details."},
                        {"section": "Results", "text": "Adjusted odds ratio for cessation."},
                    ],
                    "tables": [],
                },
                "abstract": "Drug improved smoking cessation.",
            }
        ],
        "gold_partial_analysis_settings": [
            {
                "candidate_id": "c1",
                "outcome_concept": "Smoking cessation",
                "data_type": "Dichotomous",
                "candidate_effect_measure": "Risk Ratio",
                "comparisons": ["Drug versus placebo"],
                "arm_pairs": [{"experimental_arm": "Drug", "control_arm": "Placebo"}],
            }
        ],
        "evidence_coverage": {"coverage_level": "HIGH"},
    }



def test_conditional_cli_smoke_flow_with_strategy_variant(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.jsonl"
    benchmark_path.write_text(f"{json.dumps(_benchmark_review())}\n", encoding="utf-8")

    class PrepareArgs:
        pass

    prepare_args = PrepareArgs()
    prepare_args.benchmark_path = str(benchmark_path)
    prepare_args.output_dir = str(tmp_path)
    prepare_args.dev_ratio = 1.0
    prepare_args.seed = 1
    prepare_args.evidence_mode = "full-text"

    command_prepare_conditional(prepare_args)
    dataset_path = tmp_path / "conditional_splits" / "full-text" / "dev.jsonl"
    rows = load_jsonl(dataset_path)
    assert rows

    class SubsetArgs:
        pass

    subset_args = SubsetArgs()
    subset_args.dataset_path = str(dataset_path)
    subset_args.output_path = str(tmp_path / "dev_subset.jsonl")
    subset_args.task = "candidate_effect_measure"
    subset_args.evidence_mode = "full-text"
    subset_args.subset_size = 1
    subset_args.seed = 1
    command_make_conditional_subset(subset_args)
    subset_rows = load_jsonl(Path(subset_args.output_path))
    assert len(subset_rows) == 1

    class RunArgs:
        pass

    run_args = RunArgs()
    run_args.dataset_path = str(dataset_path)
    run_args.output_dir = str(tmp_path)
    run_args.backend = "mock"
    run_args.json_source = None
    run_args.api_key = None
    run_args.base_url = None
    run_args.model_name = "mock-model"
    run_args.model_version = "v1"
    run_args.split = "dev"
    run_args.task = "candidate_effect_measure"
    run_args.evidence_mode = "full-text"
    run_args.evidence_strategy = "family_aware_evidence"
    run_args.decision_strategy = "constrained_selection"
    run_args.few_shot_set = ""
    run_args.concurrency = 1
    run_args.timeout_seconds = 30
    run_args.max_retries = 0
    run_args.max_output_tokens = 1000
    run_args.rerun_failed = False
    run_args.rerun_invalid_output = False
    run_args.rerun_empty_output = False
    run_args.review_id = None
    run_args.prompt_version = ""

    command_run_conditional(run_args)
    resolved_model_name = _load_local_api_config().get("model", "") or run_args.model_name
    run_summary = load_json(
        tmp_path / "runs" / resolved_model_name / "dev" / "candidate_effect_measure" / "full-text" / "ft_familyevidence_constrainedselection" / "run_summary.json"
    )
    assert run_summary["scheduled_instance_count"] == 1
    assert run_summary["decision_strategy"] == "constrained_selection"

    class EvalArgs:
        pass

    eval_args = EvalArgs()
    eval_args.dataset_path = str(dataset_path)
    eval_args.output_dir = str(tmp_path)
    eval_args.model_name = "mock-model"
    eval_args.split = "dev"
    eval_args.task = "candidate_effect_measure"
    eval_args.evidence_mode = "full-text"
    eval_args.evidence_strategy = "family_aware_evidence"
    eval_args.decision_strategy = "constrained_selection"
    eval_args.few_shot_set = ""
    eval_args.cascade_data_type_source = "gold"
    eval_args.error_sample_size = 10
    eval_args.seed = 1

    command_evaluate_conditional(eval_args)
    aggregate = load_json(
        tmp_path / "evaluations" / resolved_model_name / "dev" / "candidate_effect_measure" / "full-text" / "ft_familyevidence_constrainedselection" / "aggregate.json"
    )
    assert aggregate["accuracy"] == 1.0
    assert aggregate["evidence_strategy"] == "family_aware_evidence"
    assert aggregate["decision_strategy"] == "constrained_selection"



def test_conditional_cli_comparisons_prompt_and_fewshot_variant_paths(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.jsonl"
    benchmark_path.write_text(f"{json.dumps(_benchmark_review())}\n", encoding="utf-8")

    class PrepareArgs:
        pass

    prepare_args = PrepareArgs()
    prepare_args.benchmark_path = str(benchmark_path)
    prepare_args.output_dir = str(tmp_path)
    prepare_args.dev_ratio = 1.0
    prepare_args.seed = 1
    prepare_args.evidence_mode = "full-text"
    command_prepare_conditional(prepare_args)
    dataset_path = tmp_path / "conditional_splits" / "full-text" / "dev.jsonl"

    class RunArgs:
        pass

    run_args = RunArgs()
    run_args.dataset_path = str(dataset_path)
    run_args.output_dir = str(tmp_path)
    run_args.backend = "mock"
    run_args.json_source = None
    run_args.api_key = None
    run_args.base_url = None
    run_args.model_name = "mock-model"
    run_args.model_version = "v1"
    run_args.split = "dev"
    run_args.task = "comparisons"
    run_args.evidence_mode = "full-text"
    run_args.evidence_strategy = "standard_fulltext_evidence"
    run_args.decision_strategy = "free_generation"
    run_args.few_shot_set = "comparisons_boundary_v1"
    run_args.concurrency = 1
    run_args.timeout_seconds = 30
    run_args.max_retries = 0
    run_args.max_output_tokens = 1000
    run_args.rerun_failed = False
    run_args.rerun_invalid_output = False
    run_args.rerun_empty_output = False
    run_args.review_id = None
    run_args.prompt_version = "conditional_task_aware_v6_comparisons_review_level"

    command_run_conditional(run_args)
    resolved_model_name = _load_local_api_config().get("model", "") or run_args.model_name
    variant_dir = "comparisons_prompt_review_level_v1__fewshot_comparisons_boundary_v1"
    run_summary = load_json(
        tmp_path / "runs" / resolved_model_name / "dev" / "comparisons" / "full-text" / variant_dir / "run_summary.json"
    )
    assert run_summary["scheduled_instance_count"] == 1
    assert run_summary["few_shot_set"] == "comparisons_boundary_v1"
    assert run_summary["prompt_version"] == "conditional_task_aware_v6_comparisons_review_level"

    class EvalArgs:
        pass

    eval_args = EvalArgs()
    eval_args.dataset_path = str(dataset_path)
    eval_args.output_dir = str(tmp_path)
    eval_args.model_name = "mock-model"
    eval_args.split = "dev"
    eval_args.task = "comparisons"
    eval_args.evidence_mode = "full-text"
    eval_args.evidence_strategy = "standard_fulltext_evidence"
    eval_args.decision_strategy = "free_generation"
    eval_args.few_shot_set = "comparisons_boundary_v1"
    eval_args.prompt_version = "conditional_task_aware_v6_comparisons_review_level"
    eval_args.cascade_data_type_source = "gold"
    eval_args.error_sample_size = 10
    eval_args.seed = 1

    command_evaluate_conditional(eval_args)
    aggregate = load_json(
        tmp_path / "evaluations" / resolved_model_name / "dev" / "comparisons" / "full-text" / variant_dir / "aggregate.json"
    )
    assert aggregate["comparison_only"]["normalized_set_f1"] == 1.0
    assert aggregate["few_shot_set"] == "comparisons_boundary_v1"
    assert aggregate["prompt_version"] == "conditional_task_aware_v6_comparisons_review_level"


def test_conditional_cli_comparisons_constrained_selection_variant_paths(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.jsonl"
    benchmark_path.write_text(f"{json.dumps(_benchmark_review())}\n", encoding="utf-8")

    class PrepareArgs:
        pass

    prepare_args = PrepareArgs()
    prepare_args.benchmark_path = str(benchmark_path)
    prepare_args.output_dir = str(tmp_path)
    prepare_args.dev_ratio = 1.0
    prepare_args.seed = 1
    prepare_args.evidence_mode = "full-text"
    command_prepare_conditional(prepare_args)
    dataset_path = tmp_path / "conditional_splits" / "full-text" / "dev.jsonl"

    class RunArgs:
        pass

    run_args = RunArgs()
    run_args.dataset_path = str(dataset_path)
    run_args.output_dir = str(tmp_path)
    run_args.backend = "mock"
    run_args.json_source = None
    run_args.api_key = None
    run_args.base_url = None
    run_args.model_name = "mock-model"
    run_args.model_version = "v1"
    run_args.split = "dev"
    run_args.task = "comparisons"
    run_args.evidence_mode = "full-text"
    run_args.evidence_strategy = "standard_fulltext_evidence"
    run_args.decision_strategy = "constrained_selection"
    run_args.few_shot_set = ""
    run_args.concurrency = 1
    run_args.timeout_seconds = 30
    run_args.max_retries = 0
    run_args.max_output_tokens = 1000
    run_args.rerun_failed = False
    run_args.rerun_invalid_output = False
    run_args.rerun_empty_output = False
    run_args.review_id = None
    run_args.prompt_version = ""

    command_run_conditional(run_args)
    resolved_model_name = _load_local_api_config().get("model", "") or run_args.model_name
    variant_dir = "comparisons_constrained_selection_v1"
    run_summary = load_json(
        tmp_path / "runs" / resolved_model_name / "dev" / "comparisons" / "full-text" / variant_dir / "run_summary.json"
    )
    assert run_summary["decision_strategy"] == "constrained_selection"
    assert run_summary["prompt_version"] == "conditional_task_aware_v7_comparisons_selection"

    class EvalArgs:
        pass

    eval_args = EvalArgs()
    eval_args.dataset_path = str(dataset_path)
    eval_args.output_dir = str(tmp_path)
    eval_args.model_name = "mock-model"
    eval_args.split = "dev"
    eval_args.task = "comparisons"
    eval_args.evidence_mode = "full-text"
    eval_args.evidence_strategy = "standard_fulltext_evidence"
    eval_args.decision_strategy = "constrained_selection"
    eval_args.few_shot_set = ""
    eval_args.prompt_version = ""
    eval_args.cascade_data_type_source = "gold"
    eval_args.error_sample_size = 10
    eval_args.seed = 1

    command_evaluate_conditional(eval_args)
    aggregate = load_json(
        tmp_path / "evaluations" / resolved_model_name / "dev" / "comparisons" / "full-text" / variant_dir / "aggregate.json"
    )
    assert aggregate["decision_strategy"] == "constrained_selection"
    assert aggregate["prompt_version"] == "conditional_task_aware_v7_comparisons_selection"
