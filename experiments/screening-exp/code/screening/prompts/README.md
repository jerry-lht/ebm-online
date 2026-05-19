# Prompt Registry

This directory stores experiment-facing prompt assets for screening methods.

## Direct Baseline Layout

The direct LLM baseline uses a file-backed prompt registry:

- `direct.py`: prompt registry, structured prompt context builder, and renderer
- `direct/v0.txt`: baseline binary-decision JSON prompt template
- `direct/v1.txt`: alternate binary-decision JSON prompt template with a more explicit task/output split
- `direct/v2.txt`: benchmark-aligned conservative abstract-only template
- `direct/v3.txt`: abstract-only EBM-style title/abstract screening template with minimal output

The runner continues to call `build_direct_prompt(...)`, but prompt text is no longer hard-coded inside the runner or CLI.

## Current Experiment Contract

The current Phase 7 mainline is benchmark-aligned first.

For `CSMeD-FT abstract_only`, the prepared examples currently behave like:

- review question
- candidate title
- candidate abstract
- binary label `include | exclude`

Some examples also carry extra review metadata, but the `abstract_only` v3 prompt is written only against the benchmark task that actually exists today: review-question-conditioned title/abstract screening for whether a study is potentially eligible.

## Current Output Contract

The current Phase 7 direct baseline now has two output contracts:

- `abstract_only` with `v3`: minimal JSON containing `decision` and `main_reason`, framed as systematic-review title/abstract screening
- richer settings with `v0`/`v1`/`v2`: JSON containing `decision`, `criterion_judgments`, `failed_criterion`, `main_reason`, and `evidence_spans`

The prompt no longer asks the model to emit:

- `needs_review`
- self-reported `confidence`

This keeps the direct baseline aligned with the benchmark's native `include / exclude` label space and avoids treating self-reported confidence as a calibrated risk signal.

## How To Add A New Prompt Version

1. Create a new template file under `code/screening/prompts/direct/`, for example `v4.txt`.
2. Reuse the same placeholders already used by `v0.txt` / `v1.txt`:
   - `{prompt_version}`
   - `{example_id}`
   - `{question}`
   - `{population}`
   - `{intervention}`
   - `{comparator}`
   - `{outcome}`
   - `{study_design}`
   - `{inclusion_criteria}`
   - `{exclusion_criteria}`
   - `{candidate_block}`
   - `{json_template}`
3. Register the new version in `DIRECT_PROMPT_SPECS` inside `direct.py`.
4. Run targeted tests:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_direct_prompt.py code/tests/test_run_direct_llm.py -q
```

## How To Run A Specific Prompt Version

Use the CLI `--prompt-version` flag:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.run_direct_llm \
  --examples results/data/csmed_ft/test-small.abstract_only.examples.jsonl \
  --provider-config code/config/llm_providers.local.yaml \
  --defaults-config code/config/experiment_defaults.yaml \
  --provider openai-compatible \
  --model deepseek-ai/DeepSeek-V4-Flash \
  --input-setting abstract_only \
  --prompt-version v1 \
  --run-id csmed_ft_test_small_abs_v1_prompt_v1 \
  --workers 2 \
  --resume
```

If `--prompt-version` is omitted, the runner uses the value from `code/config/experiment_defaults.yaml`.

`v3` is abstract-only only; the runner routes `abstract_only` runs to the minimal prediction schema and keeps full-text runs on the richer schema.

## Criterion-wise Layout

Phase 8 adds a second file-backed prompt registry for `CSMeD-FT` criterion-wise screening:

- `criterion_wise.py`: prompt registry, structured prompt context builder, and renderer
- `criterion_wise/v3.txt`: raw-criteria one-shot prompt that takes review question, raw criteria prose, title, abstract, and full text, then returns minimal `criterion_judgments`
- `criterion_wise/fixed_specs_v1.txt`: prompt-only ablation that asks the model to judge only fixed `CriterionSpec` IDs
- `criterion_wise/hybrid_specs_raw_v1.txt`: prompt-only ablation that provides raw criteria context but constrains output to fixed `CriterionSpec` IDs

The criterion-wise runner performs final decision aggregation locally after parsing the model output, so the prompt never asks the model for a top-level `decision`.

## Criterion-wise Runner Contract

The current Phase 8 method is intentionally narrower than the direct baseline:

- benchmark scope: `CSMeD-FT` only
- supported settings:
  - `full_text_only`
  - `abstract_plus_full_text`
- prediction schema written to outputs: `criterion_wise_minimal_v1`

The prompt is built from:

- review question
- raw review criteria prose
- candidate title
- candidate abstract
- candidate full text

`v3` is the current raw-criteria mainline and uses `inc_*` / `exc_*` criterion keys with `text` + `judgment` only.

Supported criteria modes:

- `raw`: current one-shot mode; the model derives `inc_*` / `exc_*` keys from raw review criteria prose.
- `fixed_specs`: renders `build_csmed_criterion_specs()` output and requires the model to return exactly those criterion IDs.
- `hybrid_specs_raw`: provides raw review criteria as context but requires output to match fixed `CriterionSpec` IDs.

For `fixed_specs` and `hybrid_specs_raw`, the runner validates returned criterion IDs. Missing or unexpected IDs are recorded as prediction validation errors.

## How To Run Criterion-wise Phase 8

Example `full_text_only` run:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.run_criterion_wise \
  --examples results/data/csmed_ft/test-small.full_text_only.examples.jsonl \
  --provider-config code/config/llm_providers.local.yaml \
  --provider openai-compatible \
  --model gpt-5.4-mini \
  --input-setting full_text_only \
  --prompt-version v3 \
  --criteria-mode raw \
  --run-id csmed_ft_test_small_fulltext_criterion_v3_gpt54mini_smoke3_20260516 \
  --limit 3
```

Example `abstract_plus_full_text` run:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.run_criterion_wise \
  --examples results/data/csmed_ft/test-small.abstract_plus_full_text.examples.jsonl \
  --provider-config code/config/llm_providers.local.yaml \
  --defaults-config code/config/experiment_defaults.yaml \
  --provider openai-compatible \
  --model gpt-5.4-mini \
  --input-setting abstract_plus_full_text \
  --prompt-version v3 \
  --criteria-mode raw \
  --run-id csmed_ft_test_small_absft_criterion_v3_gpt54mini_smoke3_20260516 \
  --limit 3
```

Example fixed-spec dev ablation:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.run_criterion_wise \
  --examples results/data/csmed_ft/dev.abstract_plus_full_text.examples.jsonl \
  --provider-config code/config/llm_providers.local.yaml \
  --provider openai-compatible \
  --model gpt-5.4-mini \
  --input-setting abstract_plus_full_text \
  --prompt-version fixed_v1 \
  --criteria-mode fixed_specs \
  --run-id csmed_ft_dev_absft_criterion_fixed_v1_gpt54mini_full_20260516 \
  --workers 2 \
  --resume
```

Example hybrid fixed+raw dev ablation:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.run_criterion_wise \
  --examples results/data/csmed_ft/dev.abstract_plus_full_text.examples.jsonl \
  --provider-config code/config/llm_providers.local.yaml \
  --provider openai-compatible \
  --model gpt-5.4-mini \
  --input-setting abstract_plus_full_text \
  --prompt-version hybrid_v1 \
  --criteria-mode hybrid_specs_raw \
  --run-id csmed_ft_dev_absft_criterion_hybrid_v1_gpt54mini_full_20260516 \
  --workers 2 \
  --resume
```

## Criterion-wise Outputs

The model output contract is intentionally minimal:

```json
{
  "criterion_judgments": {
    "inc_1": {
      "text": "Adults with chronic kidney disease",
      "judgment": "yes"
    }
  }
}
```

The runner then adds the top-level fields locally:

- `decision`
- `failed_criterion`
- `main_reason`
- `evidence_spans`

It also writes `run_metadata.json`.

Important metadata fields include:

- `prediction_schema`
- `criterion_mode`
- `criteria_input_mode`
- `aggregation_status`
- `criteria_source`
- `fixed_criteria_source`
- `expected_criterion_ids`
- `criteria_probe_limit`

## Iteration Guidance

Use separate prompt versions for meaningful experimental changes instead of editing one version in place.

Recommended uses for new versions:

- adjust how aggressively the model is allowed to `exclude`
- simplify or expand the review-question interpretation
- add or remove template examples
- compare abstract-only prompt framing strategies

One current experimental caveat is benchmark-side input completeness. For some `CSMeD-FT` review/sample combinations, the prepared abstract-only examples effectively reduce to review-question wording plus candidate abstract. That is acceptable for the benchmark-aligned baseline, but it should be described honestly and not mislabeled as a structured criteria-aware setup.

Keep the Python rendering logic stable unless the placeholders or input layout must change. Most prompt experiments should only require:

- editing a `.txt` template
- registering the version
- rerunning the same command with a different `--prompt-version`

For the current dev prompt-optimization round, `test` results are frozen as exploratory baselines. Prompt and aggregation choices should be selected on `dev` only, then evaluated on `test` only after the dev decision is locked.
