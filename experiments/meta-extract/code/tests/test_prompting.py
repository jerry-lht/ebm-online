from meta_extract.prompting import (
    PROMPT_ROOT,
    PromptStrategy,
    available_prompt_variants,
    build_oracle_extraction_prompt_bundle,
    build_proposal_prompt_bundle,
    build_routed_extraction_prompt_bundle,
    build_support_prompt_bundle,
    register_prompt_strategy,
)


def _instance(data_type: str) -> dict:
    return {
        "study": {
            "sample_id": "S1",
            "review_id": "R1",
            "study_id": "Study 1",
            "study_year": "2020",
            "primary_report": {},
            "sr_title": "Review 1",
            "sr_pico": {},
            "full_content": {
                "sections": [{"heading": "Results", "text": "Outcome at 1 month in adults."}],
                "tables": [{"title": "Table 1", "rows": ["A 1.0", "B 2.0"]}],
            },
        },
        "setting_context": {
            "data_type": data_type,
            "outcome_concept": "Outcome",
            "comparison": "A versus B",
            "effect_measure": "Mean Difference",
            "subgroup_candidates": ["Adults"],
            "timepoints": ["1 month"],
            "reported_outcome_measures": ["Scale X at 1 month"],
        },
        "official_item": {
            "comparison": "A versus B",
            "subgroup": "Adults",
            "timepoints": ["1 month"],
            "match_status": "unique",
        },
        "gold_items": [{"subgroup": "Adults", "timepoints": ["1 month"], "gold_extraction_rows": []}],
    }


def test_default_prompt_bundles_expose_metadata_and_rules():
    support = build_support_prompt_bundle(_instance("Continuous"))
    support_subgroup = build_support_prompt_bundle(_instance("Continuous"), target="subgroup")
    support_timepoint = build_support_prompt_bundle(_instance("Continuous"), target="timepoint")
    routed = build_routed_extraction_prompt_bundle(_instance("Dichotomous"))

    assert support.prompt_name == "support:default"
    assert support.context_stats["section_count"] == 1
    assert "uncertain" in support.messages[0]["content"]
    assert "follow-up" in support.messages[0]["content"]
    assert "incomplete negative label" in support.messages[0]["content"]
    assert "timepoint_granularity_mismatch" in support.messages[1]["content"]
    assert '"support_target": "joint"' in support.messages[1]["content"]
    assert 'Only decide subgroup_support_status' in support_subgroup.messages[0]["content"]
    assert '"support_target": "subgroup"' in support_subgroup.messages[1]["content"]
    assert 'Only decide timepoint_support_status' in support_timepoint.messages[0]["content"]
    assert 'result itself is explicitly tied' in support_timepoint.messages[0]["content"]
    assert 'Do not require the article to repeat the exact same wording' in support_timepoint.messages[0]["content"]
    assert '"support_target": "timepoint"' in support_timepoint.messages[1]["content"]

    oracle = build_oracle_extraction_prompt_bundle(_instance("Continuous"))

    assert routed.prompt_name == "routed_extraction:default"
    assert routed.allowed_fields == ["Experimental cases", "Experimental N", "Control cases", "Control N"]
    assert "Allowed direct field names" in routed.messages[0]["content"]
    assert '"predicted_items"' in routed.messages[1]["content"]
    assert '"task_target"' in oracle.messages[1]["content"]
    assert '"unit": "official_item"' in oracle.messages[1]["content"]
    assert '"setting_context"' in oracle.messages[1]["content"]
    assert '"reported_outcome_measures": ["Scale X at 1 month"]' in oracle.messages[1]["content"]


def test_prompt_text_is_loaded_from_txt_files():
    shared = (PROMPT_ROOT / "oracle_extraction" / "default" / "shared.txt").read_text(encoding="utf-8")
    contrast = (PROMPT_ROOT / "oracle_extraction" / "default" / "contrast_level.txt").read_text(encoding="utf-8")
    bundle = build_oracle_extraction_prompt_bundle(_instance("Contrast level"))

    assert "This task is benchmark2-v2 Oracle Extraction" in shared
    assert "must output only its predicted_rows" in shared
    assert "setting_context defines the analysis setting" in shared
    assert "unique and multiple are valid extraction tasks" in shared
    assert "Allowed direct field names: GIV Mean, GIV SE, Mean, Variance, CI start, CI end, Footnotes." in contrast
    assert "Only emit contrast-level fields that are explicitly supported for this official item" in contrast
    assert "GIV Mean" in bundle.messages[0]["content"]
    assert bundle.allowed_fields == ["GIV Mean", "GIV SE", "Mean", "Variance", "CI start", "CI end", "Footnotes"]


def test_proposal_prompt_variants_include_ebm_and_split_targets():
    ebm = build_proposal_prompt_bundle(_instance("Continuous"), variant="negative_examples_ebm")
    subgroup = build_proposal_prompt_bundle(_instance("Continuous"), variant="negative_examples_split", target="subgroup")
    timepoint = build_proposal_prompt_bundle(_instance("Continuous"), variant="negative_examples_split", target="timepoint")

    assert ebm.prompt_name == "proposal:negative_examples_ebm"
    assert "analysis populations" in ebm.messages[0]["content"]
    assert "treatment arms" in ebm.messages[0]["content"]
    assert '"proposal_target": "subgroup"' in subgroup.messages[1]["content"]
    assert '"proposed_subgroups"' in subgroup.messages[1]["content"]
    assert 'Return proposed_subgroups only' in subgroup.messages[0]["content"]
    assert '"proposal_target": "timepoint"' in timepoint.messages[1]["content"]
    assert '"proposed_timepoints"' in timepoint.messages[1]["content"]
    assert 'Return proposed_timepoints only' in timepoint.messages[0]["content"]
    assert "negative_examples_split" in available_prompt_variants("proposal")
    assert "negative_examples_ebm" in available_prompt_variants("proposal")


def test_prompt_strategy_registry_supports_new_variants():
    register_prompt_strategy(
        PromptStrategy(
            task_name="proposal",
            variant="compact-test",
            section_limit=2,
            table_limit=1,
            shared_rules=("Shared compact rule.",),
            data_type_rules={"__default__": ("Fallback rule.",)},
            payload_builder=lambda instance, data_type, sections, tables, allowed_fields: {
                "study": {"study_id": instance["study"]["study_id"]},
                "setting_context": {"data_type": data_type},
                "evidence_sections": sections,
                "evidence_tables": tables,
                "allowed": allowed_fields,
            },
        ),
        replace=True,
    )
    bundle = build_proposal_prompt_bundle(_instance("Continuous"), variant="compact-test")
    assert bundle.prompt_name == "proposal:compact-test"
    assert bundle.messages[0]["content"] == "Shared compact rule.\nFallback rule."
    assert "compact-test" in available_prompt_variants("proposal")


def test_oracle_few_shot_variant_is_registered_and_uses_examples():
    bundle = build_oracle_extraction_prompt_bundle(_instance("Contrast level"), variant="few_shot")

    assert bundle.prompt_name == "oracle_extraction:few_shot"
    assert "worked examples" in (PROMPT_ROOT / "oracle_extraction" / "few_shot" / "__default__.txt").read_text(encoding="utf-8").lower()
    assert "Worked example:" in bundle.messages[0]["content"]
    assert "GIV Mean = ln(1.29) = 0.2546" in bundle.messages[0]["content"]
    assert "Select one target row or one target row block before copying any numbers." in bundle.messages[0]["content"]
    assert bundle.context_stats["table_count"] == 1


def test_oracle_few_shot_rules_emphasize_row_alignment_for_dichotomous_and_continuous():
    dich_bundle = build_oracle_extraction_prompt_bundle(_instance("Dichotomous"), variant="few_shot")
    cont_bundle = build_oracle_extraction_prompt_bundle(_instance("Continuous"), variant="few_shot")

    assert "official_item subgroup = Superficial infection" in dich_bundle.messages[0]["content"]
    assert "Do not assemble one predicted row from one outcome row plus another row's arm sizes." in dich_bundle.messages[0]["content"]
    assert "If you cannot identify one target dichotomous result row with both arms, return no row instead of guessing." in dich_bundle.messages[0]["content"]
    assert "official_item timepoint = postintervention" in cont_bundle.messages[0]["content"]
    assert "If only N is visible, return no row." in cont_bundle.messages[0]["content"]
    assert "Do not build one predicted row by taking mean and SD from one row and N from a different row" in cont_bundle.messages[0]["content"]


def test_oracle_results_slice_variants_filter_to_results_sections():
    inst = _instance("Continuous")
    inst["study"]["full_content"]["sections"] = [
        {"heading": "Introduction", "text": "Background only."},
        {"heading": "Methods", "text": "Methods only."},
        {"heading": "Results", "text": "Outcome at 1 month in adults."},
        {"heading": "Discussion", "text": "Discussion only."},
    ]
    bundle = build_oracle_extraction_prompt_bundle(inst, variant="results_slice")
    few_shot_bundle = build_oracle_extraction_prompt_bundle(inst, variant="results_slice_few_shot")

    assert bundle.prompt_name == "oracle_extraction:results_slice"
    assert few_shot_bundle.prompt_name == "oracle_extraction:results_slice_few_shot"
    assert bundle.context_stats["section_filter"] == "abstract_or_results"
    assert few_shot_bundle.context_stats["section_filter"] == "abstract_or_results"
    assert bundle.context_stats["section_count"] == 1
    assert few_shot_bundle.context_stats["section_count"] == 1
    assert "Example:" in few_shot_bundle.messages[0]["content"] or "Worked example:" in few_shot_bundle.messages[0]["content"]
