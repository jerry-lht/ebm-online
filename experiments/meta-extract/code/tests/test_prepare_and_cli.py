from pathlib import Path

from meta_extract import predictors
from meta_extract.instances import prepare_instances
from meta_extract.io_utils import iter_jsonl, read_json
from meta_extract.predictors import rerun_failures, run_oracle_extraction, run_proposal, run_routed_extraction, run_support
from meta_extract.reporting import build_report
from meta_extract.runtime import resolve_task_paths
from meta_extract.scoring import score_all, score_oracle_extraction, score_proposal, score_routed_extraction, score_support


FIXTURE = """{"sample_id":"S1","review_id":"R1","study_id":"Study 1","study_year":"2020","primary_report":{},"sr_title":"Review 1","sr_pico":{},"full_content":{"sections":[{"heading":"Results","text":"Outcome was measured at 1 month in adults using Scale X."}],"tables":[{"title":"Table 1","rows":["Arm A 1.0 0.5 10","Arm B 2.0 0.7 11","Arm A2 1.5 0.6 12","Arm B2 2.5 0.8 13"]}]},"gold_partial_analysis_settings":[{"candidate_id":"C1","analysis_label":"Outcome","outcome_concept":"Outcome","data_type":"Continuous","candidate_effect_measure":"Mean Difference","comparisons":["A versus B"],"arm_pairs":[{"experimental_arm":"A","control_arm":"B"}],"subgroup_candidates":["Adults"],"timepoints":["1 month"],"reported_outcome_measures":["Scale X at 1 month"],"analysis_items":[{"item_id":"I1","match_status":"multiple","comparison":"A versus B","subgroup":"Adults","timepoints":["1 month"],"gold_extraction_rows":[{"extraction_row_id":"R1","row_variant_index":1,"data_type":"Continuous","effect_measure":"Mean Difference","direct_extraction_fields":[{"field":"Experimental mean","value":"1.0"},{"field":"Experimental SD","value":"0.5"},{"field":"Experimental N","value":"10"},{"field":"Control mean","value":"2.0"},{"field":"Control SD","value":"0.7"},{"field":"Control N","value":"11"}],"non_direct_fields":[]},{"extraction_row_id":"R2","row_variant_index":2,"data_type":"Continuous","effect_measure":"Mean Difference","direct_extraction_fields":[{"field":"Experimental mean","value":"1.5"},{"field":"Experimental SD","value":"0.6"},{"field":"Experimental N","value":"12"},{"field":"Control mean","value":"2.5"},{"field":"Control SD","value":"0.8"},{"field":"Control N","value":"13"}],"non_direct_fields":[]}]}]}]}
{"sample_id":"S2","review_id":"R2","study_id":"Study 2","study_year":"2021","primary_report":{},"sr_title":"Review 2","sr_pico":{},"full_content":{"sections":[{"heading":"Results","text":"Adults were followed at 6 months."}],"tables":[{"title":"Table 2","rows":["Drug 4/40","Placebo 7/42"]}]},"gold_partial_analysis_settings":[{"candidate_id":"C2","analysis_label":"Outcome","outcome_concept":"Outcome","data_type":"Dichotomous","candidate_effect_measure":"Risk Ratio","comparisons":["Drug versus placebo"],"arm_pairs":[{"experimental_arm":"Drug","control_arm":"Placebo"}],"subgroup_candidates":["Adults","Teens"],"timepoints":["6 months"],"reported_outcome_measures":[],"analysis_items":[{"item_id":"I2","match_status":"unique","comparison":"Drug versus placebo","subgroup":"Adults","timepoints":["6 months"],"gold_extraction_rows":[{"extraction_row_id":"R3","row_variant_index":1,"data_type":"Dichotomous","effect_measure":"Risk Ratio","direct_extraction_fields":[{"field":"Experimental cases","value":"4"},{"field":"Experimental N","value":"40"},{"field":"Control cases","value":"7"},{"field":"Control N","value":"42"}],"non_direct_fields":[]}]},{"item_id":"I3","match_status":"no_match","comparison":"Drug versus placebo","subgroup":"Teens","timepoints":[],"gold_extraction_rows":[]}]}]}
{"sample_id":"S3","review_id":"R3","study_id":"Study 3","study_year":"2022","primary_report":{},"sr_title":"Review 3","sr_pico":{},"full_content":{"sections":[{"heading":"Results","text":"Forest plot reported GIV mean estimates with confidence intervals and follow-up footnotes at post-intervention."}],"tables":[{"title":"Table 3","rows":["Row1 GIV Mean 0.5 GIV SE 0.1 CI -0.2 to 1.2","Row2 GIV Mean 0.7 GIV SE 0.2 CI 0.1 to 1.3"]}]},"gold_partial_analysis_settings":[{"candidate_id":"C3","analysis_label":"Outcome","outcome_concept":"Outcome","data_type":"Contrast level","candidate_effect_measure":"Std. Mean Difference","comparisons":["Intervention versus control"],"arm_pairs":[{"experimental_arm":"Intervention","control_arm":"Control"}],"subgroup_candidates":[],"timepoints":["post intervention"],"reported_outcome_measures":[],"analysis_items":[{"item_id":"I4","match_status":"multiple","comparison":"Intervention versus control","subgroup":null,"timepoints":["post intervention"],"gold_extraction_rows":[{"extraction_row_id":"R4","row_variant_index":1,"data_type":"Contrast level","effect_measure":"Std. Mean Difference","direct_extraction_fields":[],"non_direct_fields":[{"field":"GIV Mean","value":"0.5","role":"conditionally_extractable"},{"field":"GIV SE","value":"0.1","role":"conditionally_extractable"},{"field":"CI start","value":"-0.2","role":"conditionally_extractable"},{"field":"CI end","value":"1.2","role":"conditionally_extractable"},{"field":"Footnotes","value":"Follow-up: 10 weeks","role":"conditionally_extractable"}]},{"extraction_row_id":"R5","row_variant_index":2,"data_type":"Contrast level","effect_measure":"Std. Mean Difference","direct_extraction_fields":[],"non_direct_fields":[{"field":"GIV Mean","value":"0.7","role":"conditionally_extractable"},{"field":"GIV SE","value":"0.2","role":"conditionally_extractable"},{"field":"CI start","value":"0.1","role":"conditionally_extractable"},{"field":"CI end","value":"1.3","role":"conditionally_extractable"},{"field":"Footnotes","value":"Follow-up: 24 weeks","role":"conditionally_extractable"}]}]}]}]}
"""


def _prepare_run_dir(tmp_path: Path) -> tuple[Path, Path]:
    dataset_path = tmp_path / "benchmark.jsonl"
    dataset_path.write_text(FIXTURE, encoding="utf-8")
    run_dir = tmp_path / "run"
    prepare_instances(dataset_path=dataset_path, output_dir=run_dir / "instances", dev_fraction=1.0)
    return dataset_path, run_dir


def test_prepare_and_score_oracle_pipeline(tmp_path: Path):
    _, run_dir = _prepare_run_dir(tmp_path)
    run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    run_proposal(instances_path=run_dir / "instances" / "proposal_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    run_oracle_extraction(instances_path=run_dir / "instances" / "oracle_extraction_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    run_routed_extraction(instances_path=run_dir / "instances" / "routed_extraction_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)

    support_summary = score_support(instances_path=run_dir / "instances" / "support_instances.jsonl", predictions_path=run_dir / "predictions" / "support_predictions.jsonl", output_dir=run_dir / "scores")
    proposal_summary = score_proposal(instances_path=run_dir / "instances" / "proposal_instances.jsonl", predictions_path=run_dir / "predictions" / "proposal_predictions.jsonl", output_dir=run_dir / "scores")
    oracle_summary = score_oracle_extraction(instances_path=run_dir / "instances" / "oracle_extraction_instances.jsonl", predictions_path=run_dir / "predictions" / "oracle_extraction_predictions.jsonl", output_dir=run_dir / "scores")
    routed_summary = score_routed_extraction(instances_path=run_dir / "instances" / "routed_extraction_instances.jsonl", predictions_path=run_dir / "predictions" / "routed_extraction_predictions.jsonl", output_dir=run_dir / "scores")

    contrast_item = next(row for row in iter_jsonl(run_dir / "instances" / "oracle_extraction_instances.jsonl") if row["setting_context"]["data_type"] == "Contrast level")
    contrast_fields = {field["field"] for gold_row in contrast_item["gold_extraction_rows"] for field in gold_row["direct_extraction_fields"]}

    assert support_summary["primary_metrics"]["joint_support_consistency"] == 1.0
    assert proposal_summary["primary_metrics"]["structured"]["f1"] == 1.0
    assert proposal_summary["observed_primary_metrics"]["structured"]["f1"] == 1.0
    assert proposal_summary["error_buckets"]["supported_extra_count"] == 0
    assert oracle_summary["primary_metrics"]["field"]["f1"] == 1.0
    assert oracle_summary["per_data_type"]["Contrast level"]["field"]["f1"] == 1.0
    assert oracle_summary["per_match_status"]["multiple"]["instances"] == 2
    assert oracle_summary["per_match_status"]["no_match"]["scored_instances"] == 0
    assert routed_summary["primary_metrics"]["field"]["f1"] == 1.0
    assert routed_summary["primary_metrics"]["setting_success_rate"] == 1.0
    assert {"GIV Mean", "GIV SE", "CI start", "CI end", "Footnotes"}.issubset(contrast_fields)


def test_llm_modes_use_stubbed_predictors(tmp_path: Path, monkeypatch):
    _, run_dir = _prepare_run_dir(tmp_path)

    monkeypatch.setattr(
        predictors,
        "_support_llm_predict",
        lambda row, prompt_variant="default": {
            "subgroup_support_status": "supported",
            "timepoint_support_status": "supported",
            "prediction_metadata": {"model": "stub-model", "prompt_version": predictors.PROMPT_VERSION, "prompt_name": f"support:{prompt_variant}", "data_type": row["setting_context"].get("data_type"), "context_stats": {"section_count": 1, "table_count": 1, "allowed_field_count": 0}},
            "prediction_stats": {"empty_prediction_count": 0},
        },
    )
    monkeypatch.setattr(
        predictors,
        "_proposal_llm_predict",
        lambda row, prompt_variant="default": {
            "proposed_items": [{"subgroup": item.get("subgroup"), "timepoints": item.get("timepoints") or []} for item in row.get("gold_items") or []],
            "prediction_metadata": {"model": "stub-model", "prompt_version": predictors.PROMPT_VERSION, "prompt_name": f"proposal:{prompt_variant}", "data_type": row["setting_context"].get("data_type"), "context_stats": {"section_count": 1, "table_count": 1, "allowed_field_count": 0}},
            "prediction_stats": {"empty_prediction_count": 0},
        },
    )
    monkeypatch.setattr(
        predictors,
        "_oracle_extraction_llm_predict",
        lambda row, prompt_variant="default": {
            "predicted_rows": row.get("gold_extraction_rows") or [],
            "prediction_metadata": {"model": "stub-model", "prompt_version": predictors.PROMPT_VERSION, "prompt_name": f"oracle_extraction:{prompt_variant}", "data_type": row["setting_context"].get("data_type"), "context_stats": {"section_count": 1, "table_count": 1, "allowed_field_count": len(predictors.DIRECT_FIELDS_BY_DATA_TYPE[row["setting_context"]["data_type"]])}},
            "prediction_stats": {"empty_prediction_count": 0, "complete_row_count": len(row.get("gold_extraction_rows") or [])},
        },
    )
    monkeypatch.setattr(
        predictors,
        "_routed_extraction_llm_predict",
        lambda row, prompt_variant="default": {
            "predicted_items": [{"subgroup": item.get("subgroup"), "timepoints": item.get("timepoints") or [], "predicted_rows": item.get("gold_extraction_rows") or []} for item in row.get("gold_items") or []],
            "prediction_metadata": {"model": "stub-model", "prompt_version": predictors.PROMPT_VERSION, "prompt_name": f"routed_extraction:{prompt_variant}", "data_type": row["setting_context"].get("data_type"), "context_stats": {"section_count": 1, "table_count": 1, "allowed_field_count": len(predictors.DIRECT_FIELDS_BY_DATA_TYPE[row["setting_context"]["data_type"]])}},
            "prediction_stats": {"empty_prediction_count": 0},
        },
    )

    support = run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="llm", show_progress=False)
    proposal = run_proposal(instances_path=run_dir / "instances" / "proposal_instances.jsonl", run_dir=run_dir, split="dev", mode="llm", show_progress=False)
    oracle = run_oracle_extraction(instances_path=run_dir / "instances" / "oracle_extraction_instances.jsonl", run_dir=run_dir, split="dev", mode="llm", show_progress=False)
    routed = run_routed_extraction(instances_path=run_dir / "instances" / "routed_extraction_instances.jsonl", run_dir=run_dir, split="dev", mode="llm", show_progress=False)

    assert support["mode"] == "llm"
    assert proposal["mode"] == "llm"
    assert oracle["mode"] == "llm"
    assert routed["mode"] == "llm"


def test_build_report_writes_structured_tables(tmp_path: Path):
    _, run_dir = _prepare_run_dir(tmp_path)
    run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    run_proposal(instances_path=run_dir / "instances" / "proposal_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    run_oracle_extraction(instances_path=run_dir / "instances" / "oracle_extraction_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    run_routed_extraction(instances_path=run_dir / "instances" / "routed_extraction_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    score_all(run_dir=run_dir)
    manifest = build_report(score_dir=run_dir / "scores", output_path=run_dir / "reports")

    assert (run_dir / "reports" / "main_table.csv").exists()
    assert (run_dir / "reports" / "representative_failures.csv").exists()
    assert (run_dir / "reports" / "per_match_status.csv").exists()
    assert manifest["tables"]["per_field"] == "per_field.csv"
    assert manifest["tables"]["per_match_status"] == "per_match_status.csv"


def test_resume_skips_existing_predictions(tmp_path: Path):
    _, run_dir = _prepare_run_dir(tmp_path)
    first = run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    second = run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", resume=True, show_progress=False)

    assert first["completed_now"] > 0
    assert second["completed_now"] == 0
    assert second["skipped_existing"] == first["instances"]


def test_failed_instances_and_rerun_failures(tmp_path: Path, monkeypatch):
    _, run_dir = _prepare_run_dir(tmp_path)
    calls = {"count": 0}

    def raising_predict(row, mode, *, prompt_variant="default"):
        calls["count"] += 1
        if calls["count"] <= 1:
            raise ValueError("boom")
        return {"instance_id": row["instance_id"], "split": row["split"], "task_name": "proposal", "proposed_items": [], "prediction_metadata": {"mode": mode}, "prediction_stats": {"empty_prediction_count": 1}}

    monkeypatch.setattr(predictors, "_proposal_predict_row", raising_predict)
    summary = run_proposal(instances_path=run_dir / "instances" / "proposal_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", continue_on_error=True, show_progress=False)
    failed_path = run_dir / "predictions" / "proposal_failed_instances.jsonl"
    failed_rows = list(iter_jsonl(failed_path))
    assert summary["failed_now"] == 1
    assert len(failed_rows) == 1

    monkeypatch.setattr(
        predictors,
        "_proposal_predict_row",
        lambda row, mode, *, prompt_variant="default": {"instance_id": row["instance_id"], "split": row["split"], "task_name": "proposal", "proposed_items": [], "prediction_metadata": {"mode": mode}, "prediction_stats": {"empty_prediction_count": 1}},
    )
    rerun_summary = rerun_failures(task_name="proposal", run_dir=run_dir, mode="oracle", show_progress=False)
    assert rerun_summary["completed_now"] == 1


def test_parse_errors_write_empty_predictions(tmp_path: Path, monkeypatch):
    _, run_dir = _prepare_run_dir(tmp_path)

    def bad_predict(row, prompt_variant="default"):
        raise ValueError("parse fail")

    monkeypatch.setattr(predictors, "_support_llm_predict", bad_predict)
    run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="llm", show_progress=False)
    rows = list(iter_jsonl(run_dir / "predictions" / "support_predictions.jsonl"))
    assert rows[0]["subgroup_support_status"] == "not_supported"
    assert rows[0]["prediction_stats"]["parse_error"].startswith("ValueError")


def test_llm_parse_repair_recovers_prediction(tmp_path: Path, monkeypatch):
    _, run_dir = _prepare_run_dir(tmp_path)

    monkeypatch.setattr(predictors, "_llm_text_response", lambda messages, model: "not json at all")
    monkeypatch.setattr(
        predictors,
        "repair_json_payload",
        lambda model, raw_text: {
            "subgroup_support_status": "supported",
            "timepoint_support_status": "uncertain",
            "uncertain_reasons": ["insufficient_evidence"],
        },
    )

    run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="llm", show_progress=False)
    rows = list(iter_jsonl(run_dir / "predictions" / "support_predictions.jsonl"))
    assert rows[0]["subgroup_support_status"] == "supported"
    assert rows[0]["timepoint_support_status"] == "uncertain"
    assert rows[0]["prediction_stats"]["json_repair_attempted"] == 2
    assert rows[0]["prediction_stats"]["json_repair_succeeded"] == 2


def test_support_llm_mode_uses_split_calls(tmp_path: Path, monkeypatch):
    _, run_dir = _prepare_run_dir(tmp_path)
    calls = []

    def fake_target_predict(row, *, prompt_variant, target):
        calls.append(target)
        if target == "subgroup":
            return ({"subgroup_support_status": "supported"}, {"prompt_name": "support:default", "data_type": row["setting_context"]["data_type"], "context_stats": {}}, {"uncertain_reason_count": 0, "uncertain_reasons": [], "empty_prediction_count": 0, "json_repair_attempted": 0, "json_repair_succeeded": 0})
        return ({"timepoint_support_status": "not_supported"}, {"prompt_name": "support:default", "data_type": row["setting_context"]["data_type"], "context_stats": {}}, {"uncertain_reason_count": 0, "uncertain_reasons": [], "empty_prediction_count": 0, "json_repair_attempted": 0, "json_repair_succeeded": 0})

    monkeypatch.setattr(predictors, "_support_target_llm_predict", fake_target_predict)
    run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="llm", show_progress=False)
    rows = list(iter_jsonl(run_dir / "predictions" / "support_predictions.jsonl"))
    assert calls[:2] == ["subgroup", "timepoint"]
    assert rows[0]["subgroup_support_status"] == "supported"
    assert rows[0]["timepoint_support_status"] == "not_supported"
    assert rows[0]["prediction_metadata"]["support_call_mode"] == "split"


def test_score_support_filters_to_prediction_split(tmp_path: Path):
    _, run_dir = _prepare_run_dir(tmp_path)
    prepare_instances(
        dataset_path=tmp_path / "benchmark.jsonl",
        output_dir=run_dir / "instances",
        dev_fraction=0.5,
        split_seed="meta-extract-benchmark2-v2-split-v1",
    )

    support_rows = list(iter_jsonl(run_dir / "instances" / "support_instances.jsonl"))
    dev_count = sum(1 for row in support_rows if row["split"] == "dev")
    test_count = sum(1 for row in support_rows if row["split"] == "test")
    assert dev_count > 0
    assert test_count > 0

    run_support(
        instances_path=run_dir / "instances" / "support_instances.jsonl",
        run_dir=run_dir,
        split="dev",
        mode="oracle",
        show_progress=False,
    )
    summary = score_support(
        instances_path=run_dir / "instances" / "support_instances.jsonl",
        predictions_path=run_dir / "predictions" / "support_predictions.jsonl",
        output_dir=run_dir / "scores",
    )

    assert summary["instances"] == dev_count
    assert summary["scored_instances"] == dev_count
    assert summary["requested_split"] == "dev"


def test_proposal_llm_mode_uses_split_calls_for_split_variant(tmp_path: Path, monkeypatch):
    _, run_dir = _prepare_run_dir(tmp_path)
    calls = []

    def fake_target_predict(row, *, prompt_variant, target):
        calls.append((prompt_variant, target))
        if target == "subgroup":
            return ({"proposed_subgroups": ["Adults"]}, {"prompt_name": "proposal:negative_examples_split", "data_type": row["setting_context"]["data_type"], "context_stats": {}}, {"proposed_subgroup_count": 1, "empty_prediction_count": 0, "json_repair_attempted": 0, "json_repair_succeeded": 0})
        return ({"proposed_timepoints": ["1 month"]}, {"prompt_name": "proposal:negative_examples_split", "data_type": row["setting_context"]["data_type"], "context_stats": {}}, {"proposed_timepoint_count": 1, "empty_prediction_count": 0, "json_repair_attempted": 0, "json_repair_succeeded": 0})

    monkeypatch.setattr(predictors, "_proposal_target_llm_predict", fake_target_predict)
    run_proposal(
        instances_path=run_dir / "instances" / "proposal_instances.jsonl",
        run_dir=run_dir,
        split="dev",
        mode="llm",
        prompt_variant="negative_examples_split",
        show_progress=False,
    )
    rows = list(iter_jsonl(run_dir / "predictions" / "proposal_predictions.jsonl"))
    assert calls[:2] == [("negative_examples_split", "subgroup"), ("negative_examples_split", "timepoint")]
    assert rows[0]["proposed_items"] == [{"subgroup": "adults", "timepoints": ["1 month"]}]
    assert rows[0]["prediction_metadata"]["proposal_call_mode"] == "split"


def test_prepare_data_target_split_filters_before_max_settings(tmp_path: Path):
    dataset_path = tmp_path / "benchmark.jsonl"
    dataset_path.write_text(FIXTURE, encoding="utf-8")
    run_dir = tmp_path / "targeted_run"

    prepare_instances(
        dataset_path=dataset_path,
        output_dir=run_dir / "instances",
        dev_fraction=0.5,
        split_seed="meta-extract-benchmark2-v2-split-v1",
        max_settings=1,
        target_split="dev",
    )

    proposal_rows = list(iter_jsonl(run_dir / "instances" / "proposal_instances.jsonl"))
    summary = read_json(run_dir / "instances" / "prepare_data_summary.json")
    manifest = read_json(run_dir / "instances" / "split_manifest.json")

    assert len(proposal_rows) == 1
    assert {row["split"] for row in proposal_rows} == {"dev"}
    assert summary["target_split"] == "dev"
    assert manifest["target_split"] == "dev"


def test_prepare_data_summary_and_run_manifests(tmp_path: Path):
    _, run_dir = _prepare_run_dir(tmp_path)
    run_support(instances_path=run_dir / "instances" / "support_instances.jsonl", run_dir=run_dir, split="dev", mode="oracle", show_progress=False)
    prepare_summary = read_json(run_dir / "instances" / "prepare_data_summary.json")
    manifest = read_json(run_dir / "manifests" / "support_run_manifest.json")
    assert prepare_summary["counts"]["support_instances"] > 0
    assert prepare_summary["target_split"] is None
    assert manifest["task_name"] == "support"


def test_task_paths_resolve_to_run_dir_layout(tmp_path: Path):
    run_dir = tmp_path / "run"
    paths = resolve_task_paths(task_name="routed_extraction", run_dir=run_dir)
    assert paths.instances_path.name == "routed_extraction_instances.jsonl"
    assert paths.predictions_path.parent.name == "predictions"
    assert paths.task_summary_path.name == "routed_extraction_summary.json"
