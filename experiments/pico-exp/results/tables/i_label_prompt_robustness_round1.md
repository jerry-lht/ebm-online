# I-Label Prompt Robustness Round 1

## Goal

This round evaluates single-label `I` extraction on the full `191`-document test set with a judge-first decision rule.

Only one prompt idea was isolated in this round:

- `representative mention`

The broader `trial-arm semantic unit` / `research-role boundary` rewrite was intentionally deferred.

## Shared Runtime

All four arms used the same runtime settings:

- examples: `results/data/test.examples.jsonl`
- provider config: `code/config/llm_providers.yaml`
- model: `gpt-5.2`
- provider base URL: `https://api.zyai.online/v1`
- workers: `16`
- timeout: `300s`
- label target: `I`
- extraction contract: `{"interventions":[...]}`

All runs were followed by:

1. inference
2. validator quality
3. text metrics
4. LLM judge

## Arm Definitions

- `A0 baseline`
  - run dir: `results/preds/llm/i_single_real_test191_2026-05-16_r1`
  - prompt: `few_shot_text_bestof_split_v1_i_only`
  - few-shot: `results/data/few_shot_text_bestof_split_i.examples.jsonl`

- `A1 fewshot_only`
  - run dir: `results/preds/llm/i_label_prompt_robustness_round1_A1_fewshot_only`
  - prompt: `few_shot_text_bestof_split_v1_i_only`
  - few-shot: `results/data/few_shot_text_bestof_split_i_round1_rep.examples.jsonl`

- `A2 rep_only`
  - run dir: `results/preds/llm/i_label_prompt_robustness_round1_A2_rep_only`
  - prompt: `few_shot_text_bestof_split_v2_i_only`
  - few-shot: `results/data/few_shot_text_bestof_split_i.examples.jsonl`

- `A3 fewshot_plus_rep`
  - run dir: `results/preds/llm/i_label_prompt_robustness_round1_A3_fewshot_plus_rep`
  - prompt: `few_shot_text_bestof_split_v2_i_only`
  - few-shot: `results/data/few_shot_text_bestof_split_i_round1_rep.examples.jsonl`

## Judge-First Comparison

Ranking order for this round:

1. `I.overall_verdict.strong`
2. `I.completeness.complete`
3. `I.accuracy.accurate`
4. `I.noise.low`

| arm | strong | complete | accurate | low_noise | I norm F1 | written_spans | ambiguous_match | response_items | failed_rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A0 baseline | 0.440 | 0.503 | 0.696 | 0.482 | 0.128 | 503 | 0.230 | 669 | 0 |
| A2 rep_only | 0.424 | 0.450 | 0.738 | 0.702 | 0.097 | 403 | 0.196 | 511 | 0 |
| A1 fewshot_only | 0.387 | 0.387 | 0.817 | 0.869 | 0.102 | 318 | 0.228 | 421 | 0 |
| A3 fewshot_plus_rep | 0.372 | 0.382 | 0.801 | 0.869 | 0.102 | 297 | 0.241 | 410 | 0 |

## Hard Checks

All four arms satisfied the required non-regression gates for this round:

- inference `failed_rows == 0`
- validator `invalid_json_rate == 0`
- validator `schema_invalid_rate == 0`

Note:

- `A2` hit one transient provider-side response-shape failure during the first full pass and was recovered successfully with `--resume`.
- The resume path exposed a bookkeeping bug in `run_config.json` / `errors.jsonl`; this was fixed after the run and covered by tests.
- Final `A2` metrics above are from the recovered complete output and reflect `failed_rows == 0`.

## Interpretation

- `A0 baseline` remains the winner under the judge-first criterion.
  - It still has the best `strong` and best `complete`.
  - Its weakness is higher noise and much larger output volume.

- `A2 rep_only` is the strongest new variant.
  - It preserves most of baseline judge strength while reducing output volume substantially.
  - It also has the best `ambiguous_match_rate` among the four arms.
  - This suggests `representative mention` is directionally useful.

- `A1 fewshot_only` is the cleanest and most accurate arm.
  - It has the best `accuracy` and ties for best `low_noise`.
  - But it is too conservative and loses too much `complete`.
  - Its primary behavior is not catastrophic omission; it more often turns `complete` cases into `partial`.

- `A3 fewshot_plus_rep` does not show additive gains.
  - It is also very clean and sparse.
  - But combining the new prompt and new few-shot compounds the conservative bias and further reduces `strong` / `complete`.

## Main Takeaway

This round does not justify replacing the baseline.

The best read is:

- the new few-shot set teaches the model to be cleaner, but too aggressively suppresses arm-detail coverage
- the `representative mention` prompt idea is useful, but still needs a completeness backstop
- the combined `A3` variant over-shrinks output and should not be promoted as-is

## A1-Specific Summary

`A1` is the arm to keep in mind if the objective is cleaner and more semantically precise output.

Its pattern is:

- highest `I.accuracy`
- highest `I.noise.low`
- lower `I.completeness.complete`

Compared with `A0`, `A1` mostly changes `complete -> partial`, not `complete -> missing`.
That means it usually retains the intervention/comparator core, but drops additional arm-level semantic detail that the judge still considers necessary for a `complete` rating.

## Recommendation

Stop at this round.

For the next iteration, the most defensible starting point is:

- keep `A2` as the prompt base
- do not carry forward `A3` unchanged
- if continuing later, add only a minimal completeness safeguard such as:
  - each distinct randomized arm / comparator / control condition should appear at least once
  - do not omit a co-intervention when it changes arm identity

No further change is recommended in this round's report beyond preserving these outputs and conclusions.
