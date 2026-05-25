# CSMeD-FT Dev Two-stage Screening Summary

Date: 2026-05-16

## Cohort And Policy

- Evaluation cohort: `results/data/csmed_ft/dev.abstract_plus_full_text.examples.jsonl` (626 full-text-capable dev examples), to keep one-step and two-stage comparisons aligned.
- Stage 1 input: `results/data/csmed_ft/dev.abstract_only.examples.jsonl` (632 abstract-only dev examples).
- Stage 1 run: `results/preds/csmed_ft/dev/direct_criteria_aware/csmed_ft_dev_abstract_direct_v3_gpt54mini_full_20260516/predictions.jsonl`.
- Policy: `conservative_stage1_exclude_only_v1`.
- Stage 1 actions on the 626-example evaluation cohort: 374 sent to Stage 2, 252 auto-excluded, 0 missing Stage 2 predictions.
- Full-text workload: 374 / 626 = 0.5974; workload reduction = 0.4026.

## Results

| Pipeline | TP | TN | FP | FN | Sensitivity | Specificity | Precision | Balanced Accuracy | Macro F1 | Stage 2 workload | Workload reduction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| one-step direct abs+full | 180 | 147 | 282 | 17 | 0.9137 | 0.3427 | 0.3896 | 0.6282 | 0.5210 | 1.0000 | 0.0000 |
| two-stage abstract-only -> direct abs+full | 163 | 236 | 193 | 34 | 0.8274 | 0.5501 | 0.4579 | 0.6888 | 0.6324 | 0.5974 | 0.4026 |
| one-step criteria raw v3 | 121 | 361 | 68 | 76 | 0.6142 | 0.8415 | 0.6402 | 0.7279 | 0.7303 | 1.0000 | 0.0000 |
| two-stage abstract-only -> criteria raw v3 | 111 | 386 | 43 | 86 | 0.5635 | 0.8998 | 0.7208 | 0.7316 | 0.7447 | 0.5974 | 0.4026 |

Canonical table: `results/tables/one_step_vs_two_stage.csv`.

## Interpretation

- The direct two-stage pipeline reduces full-text workload by 40.26%, improves specificity from 0.3427 to 0.5501, and improves precision from 0.3896 to 0.4579, but sensitivity drops from 0.9137 to 0.8274.
- The criteria raw v3 two-stage pipeline also reduces full-text workload by 40.26%, improves specificity from 0.8415 to 0.8998, and improves precision from 0.6402 to 0.7208, but sensitivity drops from 0.6142 to 0.5635.
- Neither two-stage run passes the current readiness gate because both introduce false negatives and exceed the allowed sensitivity gap versus their one-step references.

## Artifacts

- Direct two-stage predictions: `results/preds/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_direct_v2_gpt54mini_20260516/predictions.jsonl`.
- Direct two-stage metrics: `results/metrics/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_direct_v2_gpt54mini_20260516.json`.
- Criteria two-stage predictions: `results/preds/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_criteria_raw_v3_gpt54mini_20260516/predictions.jsonl`.
- Criteria two-stage metrics: `results/metrics/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_criteria_raw_v3_gpt54mini_20260516.json`.
