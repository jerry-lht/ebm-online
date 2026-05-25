# CSMeD-FT Dev Prompt Ablation Summary

Date: 2026-05-16

All runs used `gpt-5.4-mini` through the local `openai-compatible` provider config. Main runs were completed with targeted retry artifacts, then merged into `full_completed` runs with `error_count=0`.

## Completed Dev Results

| Arm | Input | TP | TN | FP | FN | Sensitivity | Specificity | Precision | Balanced Acc | Macro F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct decision v2 | abstract+full text | 180 | 147 | 282 | 17 | 0.9137 | 0.3427 | 0.3896 | 0.6282 | 0.5210 |
| Direct decision v2 | full text only | 181 | 127 | 306 | 19 | 0.9050 | 0.2933 | 0.3717 | 0.5992 | 0.4828 |
| Criteria raw v3 | abstract+full text | 121 | 361 | 68 | 76 | 0.6142 | 0.8415 | 0.6402 | 0.7279 | 0.7303 |
| Criteria fixed specs v1 | abstract+full text | 21 | 417 | 12 | 176 | 0.1066 | 0.9720 | 0.6364 | 0.5393 | 0.4993 |
| Criteria hybrid specs+raw v1 | abstract+full text | 15 | 422 | 7 | 182 | 0.0761 | 0.9837 | 0.6818 | 0.5299 | 0.4770 |

Machine-readable table:

- `results/tables/csmed_ft_dev_prompt_ablation.csv`

## Interpretation

The direct decision baseline has high sensitivity but low specificity and precision. It includes most true includes, but over-includes many gold excludes.

The raw criterion-wise prompt is the best balanced arm in this batch. It trades away recall for much higher specificity and precision, and currently has the strongest balanced accuracy and macro F1.

The fixed and hybrid criteria-list arms are not viable as-is. They sharply increase specificity by excluding nearly everything, but sensitivity collapses. This supports the concern that a fixed criteria list plus hard aggregation can turn small criterion-level mistakes into hard false negatives.

## Error Analysis

Criterion aggregation status counts:

- raw: `exclude_hard` 437, `include_clear` 131, `needs_review` 58
- fixed: `exclude_hard` 593, `include_clear` 10, `needs_review` 23
- hybrid: `exclude_hard` 604, `include_clear` 10, `needs_review` 12

False negatives by trigger group:

- raw: 76 FN, including 62 from exclusion criteria judged `yes` and 14 from inclusion criteria judged `no`
- fixed: 176 FN, including 75 from exclusion criteria judged `yes` and 101 from inclusion criteria judged `no`
- hybrid: 182 FN, including 82 from exclusion criteria judged `yes` and 100 from inclusion criteria judged `no`

Detailed artifacts:

- `results/reports/csmed_ft_dev_prompt_ablation/aggregation_status_counts.csv`
- `results/reports/csmed_ft_dev_prompt_ablation/fn_by_failed_criterion.csv`

## Next Prompt Direction

Do not promote fixed/hybrid criteria-list prompts. They are useful as a negative ablation, not as an improvement.

Use the direct decision baseline and raw criteria arm as two anchors:

- Improve direct decision specificity and precision while preserving high sensitivity.
- Improve raw criteria sensitivity by making exclusion triggers stricter and reducing hard exclusion from weak evidence.

The next controlled dev experiment should test aggregation or prompt variants that require stronger evidence for `exc_* = yes` and treat weak inclusion misses as `unclear` rather than `no`.

## Next Stage: Two-stage Screening

Yes, the next phase should be a conservative two-stage method, not another test-set prompt iteration.

The rationale from this batch is:

- Direct decision is a high-sensitivity gate: it misses few gold includes, but sends too many gold excludes forward.
- Raw criteria is a more specific reviewer: it filters excludes better, but creates too many hard false negatives if used alone.
- Fixed/hybrid criteria-list prompts currently over-exclude and should not be used as the Stage 2 default without further dev-only redesign.

Initial Phase 9 design:

- Stage 1: abstract-only high-sensitivity direct screening.
- Stage 1 routing: only clearly low-risk excludes are stopped; `include`, `needs_review`, `unclear`, low-confidence, missing-evidence, or parsing-risk cases pass to Stage 2.
- Stage 2: full-text or abstract+full-text reviewer, initially comparing raw criteria vs direct decision.
- Final evaluation: report end-to-end Sensitivity, Specificity, Precision, Balanced Accuracy, Macro F1, TP/TN/FP/FN, and Stage 2 full-text workload.

The key acceptance condition is that two-stage must reduce full-text workload without materially sacrificing sensitivity relative to the one-step high-sensitivity baseline.
