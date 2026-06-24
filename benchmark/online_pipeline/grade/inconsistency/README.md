# GRADE Domain: Inconsistency

This domain evaluates the GRADE inconsistency judgement for one evidence body
aligned to a Summary of Findings row.

The method must judge whether between-study results are importantly
inconsistent. It does not re-extract study results, choose meta-analysis
models, or read SoF/gold rationale.

## Input Boundary

The benchmark adapter passes only leak-safe upstream workflow artifacts:

- `analysis_setting`: comparison, outcome, timepoint, subgroup, data type, and effect measure.
- `population_context`: outcome population when available, otherwise question P.
- `effect_estimate`: overall effect estimate and confidence interval.
- `heterogeneity`: I2, Chi2, df, p value, tau2 when available.
- `study_result_rows`: study-level result rows from the meta-analysis module.
- `subgroup_estimates` and `subgroup_difference_tests`: subgroup evidence when available.
- `study_characteristics`: matched Characteristics of Included Studies rows.

The method input intentionally excludes:

- SoF row text
- GRADE footnotes
- gold labels
- alignment rationale
- review conclusions
- web retrieval results

This restriction avoids leakage. It also means some gold downgrades based on
review-author explanation may not be fully observable to the method.

## Methods

### `method_test`

Current default and reproducible benchmark method.

It uses deterministic evidence extraction and a transparent decision profile:

1. Extract heterogeneity statistics and study-level effect patterns.
2. Build a conservative clinical/methodological heterogeneity profile from
   study rows and study characteristics.
3. Combine statistical and pattern signals into the final GRADE domain
   judgement.

The current decision policy deliberately avoids a separate mechanical override
from weak/moderate I2 plus visual effect-pattern conflict. Error analysis showed
that override created false positives.

### `method_llm_profile`

Production-style ablation method.

The LLM reads only clean local evidence and outputs a structured characteristic
profile. It does not use web, SoF text, gold labels, footnotes, alignment
rationale, or review conclusions. The final judgement remains deterministic.

Use this method for ablation or production explanation/audit when OpenAI access
is allowed and LLM profiles can be cached or precomputed. It is not the current
default benchmark method.

## Dataset

The full v3 inconsistency dataset is built from the grade v3 source.

The maintained evaluation dataset is `grade_v3_lite`. It is a balanced lite
benchmark that keeps `unclear` severity rows for downgrade yes/no evaluation but
excludes them from level/severity metrics.

`grade_v3_lite_stratified` is the recommended dev/test evaluation view. It
keeps the same 244 lite rows but rebuilds dev/test splits from the lite root
using review-grouped stratification by gold label, severity, I2 bin, study
count, and data type. This avoids the earlier dev/test difficulty gap.

Current `grade_v3_lite` distribution:

| Split | N | Gold yes | Gold no | Gold unclear severity |
| --- | ---: | ---: | ---: | ---: |
| all | 244 | 122 | 122 | 40 |
| dev | 76 | 38 | 38 | 15 |
| test | 78 | 39 | 39 | 6 |
| smoke | 6 | 3 | 3 | 1 |

All lite instances currently include `study_characteristics`.

Current `grade_v3_lite_stratified` distribution:

| Split | N | Gold yes | Gold no | Gold unclear severity |
| --- | ---: | ---: | ---: | ---: |
| dev | 122 | 61 | 61 | 20 |
| test | 122 | 61 | 61 | 20 |

## Run Commands

Run the deterministic baseline:

```bash
PYTHONPATH=backend/src:. .venv/bin/python benchmark/online_pipeline/grade/inconsistency/evaluation/runner.py \
  --dataset benchmark/online_pipeline/grade/inconsistency/datasets/grade_v3_lite_stratified/splits/test \
  --method method_test \
  --run-id test-inconsistency-lite-deterministic
```

Run the LLM characteristic-profile ablation:

```bash
PYTHONPATH=backend/src:. .venv/bin/python benchmark/online_pipeline/grade/inconsistency/evaluation/runner.py \
  --dataset benchmark/online_pipeline/grade/inconsistency/datasets/grade_v3_lite_stratified/splits/test \
  --method method_llm_profile \
  --run-id test-inconsistency-lite-llm-profile
```

LLM profiles are cached under:

```text
.cache/grade_inconsistency_llm_profile/
```

Benchmark outputs are written to:

```text
benchmark/online_pipeline/grade/inconsistency/runs/<run_id>/
```

## Current Results

`method_test` v8 on `grade_v3_lite_stratified`:

| Split | Exact | Precision | Recall | F1 | Level Exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 0.725 | 0.704 | 0.779 | 0.739 | 0.686 |
| dev | 0.721 | 0.701 | 0.770 | 0.734 | 0.667 |
| test | 0.730 | 0.706 | 0.787 | 0.744 | 0.706 |

`method_llm_profile` v8 on the earlier `grade_v3_lite` split:

| Split | Exact | Precision | Recall | F1 | Level Exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | 0.684 | 0.659 | 0.763 | 0.707 | 0.623 |
| test | 0.769 | 0.714 | 0.897 | 0.795 | 0.694 |

## Notes

See [ITERATION_NOTES.md](ITERATION_NOTES.md) for the iteration history, error
analysis, and rationale for keeping `method_test` as the current default.
