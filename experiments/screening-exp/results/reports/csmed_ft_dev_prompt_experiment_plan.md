# CSMeD-FT Dev Prompt Optimization Plan

## Status

The completed `CSMeD-FT test` criterion-wise run is frozen as an exploratory baseline:

- Run ID: `csmed_ft_test_absft_criterion_v3_gpt54mini_full_completed_20260516`
- Setting: `test.abstract_plus_full_text`
- Model: `gpt-5.4-mini`
- Completed examples: 614/614
- Metrics: sensitivity 0.6704, specificity 0.8473, precision 0.7716, balanced accuracy 0.7588, macro F1 0.7620

This baseline must not be used for prompt tuning. Prompt and aggregation choices are selected on `dev`.

The first full `dev` ablation batch is now complete. Completed results are documented in:

- `results/tables/csmed_ft_dev_prompt_ablation.csv`
- `results/reports/csmed_ft_dev_prompt_ablation/summary.md`

## Dev Data

- `results/data/csmed_ft/dev.abstract_only.examples.jsonl`: 632 examples, 197 include / 435 exclude
- `results/data/csmed_ft/dev.abstract_plus_full_text.examples.jsonl`: 626 examples, 197 include / 429 exclude
- `results/data/csmed_ft/dev.full_text_only.examples.jsonl`: 633 examples, 200 include / 433 exclude

## Experiment Arms

Primary objective: maximize balanced accuracy on full `dev`. Always report sensitivity, specificity, precision, FN, FP, macro F1, and completion/errors.

Completed runs:

- Direct decision, `abstract_plus_full_text`, prompt `v2`: `csmed_ft_dev_absft_direct_v2_gpt54mini_full_completed_20260516`
- Direct decision, `full_text_only`, prompt `v2`: `csmed_ft_dev_fulltext_direct_v2_gpt54mini_full_completed_20260516`
- Criterion-wise raw criteria, `abstract_plus_full_text`, prompt `v3`, criteria mode `raw`: `csmed_ft_dev_absft_criterion_raw_v3_gpt54mini_full_completed_20260516`
- Criterion-wise fixed specs, `abstract_plus_full_text`, prompt `fixed_v1`, criteria mode `fixed_specs`: `csmed_ft_dev_absft_criterion_fixed_v1_gpt54mini_full_completed_20260516`
- Criterion-wise hybrid raw+fixed specs, `abstract_plus_full_text`, prompt `hybrid_v1`, criteria mode `hybrid_specs_raw`: `csmed_ft_dev_absft_criterion_hybrid_v1_gpt54mini_full_completed_20260516`

All provider-backed runs use `code/config/llm_providers.local.yaml`, provider `openai-compatible`, model `gpt-5.4-mini`, `--workers 2`, and `--resume`.

Summary metrics:

| Arm | Total | TP | TN | FP | FN | Sensitivity | Specificity | Precision | Balanced Acc | Macro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct decision abstract+full text | 626 | 180 | 147 | 282 | 17 | 0.9137 | 0.3427 | 0.3896 | 0.6282 | 0.5210 |
| Direct decision full text only | 633 | 181 | 127 | 306 | 19 | 0.9050 | 0.2933 | 0.3717 | 0.5992 | 0.4828 |
| Criteria raw v3 | 626 | 121 | 361 | 68 | 76 | 0.6142 | 0.8415 | 0.6402 | 0.7279 | 0.7303 |
| Criteria fixed specs v1 | 626 | 21 | 417 | 12 | 176 | 0.1066 | 0.9720 | 0.6364 | 0.5393 | 0.4993 |
| Criteria hybrid specs+raw v1 | 626 | 15 | 422 | 7 | 182 | 0.0761 | 0.9837 | 0.6818 | 0.5299 | 0.4770 |

## Reporting

The final dev comparison table should be written to:

- `results/tables/csmed_ft_dev_prompt_ablation.csv`

Required columns:

- `run_id`
- `method`
- `input_setting`
- `prompt_version`
- `criteria_mode`
- `model`
- `sample_count`
- `success_count`
- `error_count`
- `tp`
- `tn`
- `fp`
- `fn`
- `sensitivity`
- `specificity`
- `precision`
- `balanced_accuracy`
- `macro_f1`
- `prediction_path`
- `metric_path`

Error analysis artifacts should be written under:

- `results/reports/csmed_ft_dev_prompt_ablation/`

At minimum include by-review metrics, FN/FP by failed criterion, and aggregation-status distributions for criterion-wise runs.

## Acceptance

- Every full dev run is either 100% completed or has an explicit retry-completed artifact.
- Every run is traceable through `results/tables/run_index.csv`.
- `results/tables/automation_readiness.csv` is updated for each completed run.
- The selected prompt/method is chosen only from dev metrics.
- No additional prompt tuning is performed using `test` error cases.

## Phase 8 Outcome

This dev ablation is complete and should be treated as the one-step baseline package for the next phase.

Conclusions:

- Direct decision `abstract_plus_full_text` is the high-sensitivity baseline: sensitivity 0.9137, specificity 0.3427, precision 0.3896, balanced accuracy 0.6282, macro F1 0.5210.
- Criteria raw v3 is the strongest balanced one-step baseline: sensitivity 0.6142, specificity 0.8415, precision 0.6402, balanced accuracy 0.7279, macro F1 0.7303.
- Fixed specs and hybrid specs+raw are negative ablations. They confirm that fixed criteria plus hard aggregation can over-exclude and collapse recall.
- The frozen test run remains exploratory only; subsequent prompt and policy decisions must stay on dev.

## Phase 9 Handoff

The next stage is a conservative two-stage pipeline.

Recommended first dev experiment:

- Stage 1: abstract-only direct screening optimized for high sensitivity.
- Stage 1 stop rule: stop only clear low-risk excludes; route `include`, `needs_review`, `unclear`, low-confidence, weak-evidence, and parse-risk records to Stage 2.
- Stage 2: compare raw criteria vs direct decision on full-text or abstract+full-text inputs.
- Output: `results/tables/one_step_vs_two_stage.csv` and `results/reports/csmed_ft_two_stage_dev/summary.md`.

Required metrics:

- End-to-end TP/TN/FP/FN, Sensitivity, Specificity, Precision, Balanced Accuracy, Macro F1.
- Stage 2 workload = Stage 2 input count / Stage 1 total count.
- Comparison against the one-step anchors from this file.

The target behavior is to keep sensitivity close to the direct high-sensitivity baseline while using Stage 2 to recover specificity, improve precision, and reduce full-text workload.
