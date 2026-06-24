# GRADE Indirectness Benchmark

This benchmark evaluates one GRADE domain judgement for one aligned analysis
row: whether certainty should be downgraded for indirectness.

## Method Input Boundary

Benchmark conversion lives in `evaluation/input_adapter.py`. Backend methods
must not perform benchmark-specific conversion.

Allowed method input:

- `review_scope_pico`: broad question/review PICO
- `synthesis_target_pico`: row-specific synthesis target built from
  `analysis_setting`, with population/setting fallback when unavailable
- `sof_display_context`: SoF P/I/C/O/timepoint/setting as display and fallback
  context only
- `evidence_found`: the included studies and result rows contributing evidence
- included study IDs
- study characteristics
- study result rows for the current analysis

Forbidden method input:

- SoF comments
- SoF footnotes
- source SoF row text/spans
- alignment rationale
- gold labels

This boundary simulates a real GRADE setting after meta-analysis, where the SoF
footnote is not available to the method.

The method should compare `synthesis_target_pico`, interpreted within
`review_scope_pico`, against `evidence_found`. It should not treat
`sof_display_context` as a footnote, gold rationale, or proof of directness.

Current method prompts also require `evidence_profile` and
`directness_ratings` before final judgement. The profile extracts
applicability-relevant coverage from the already-pooled evidence body, including
intervention variants, comparator/current-practice context, outcome measurement,
follow-up, setting/era context, and overall representativeness limits.
`directness_ratings` then asks whether the evidence is sufficiently direct for
each domain before the final downgrade decision.

## Datasets

`grade_v3` is the original broad dataset. Its negative labels are weak because
`severity=none` usually means indirectness was not mentioned in the footnote.

`grade_v3_lite` is the curated benchmark set:

- root: 144 rows = 48 explicit downgrade + 96 curated high-confidence no
- dev: 48 rows = 16 yes + 32 no
- test: 36 rows = 12 yes + 24 no
- smoke: 5 rows = 2 yes + 3 no

Negative examples in `grade_v3_lite` have audit records in `audit.jsonl`.

## Recommended Development Flow

Use smoke for interface checks:

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/grade/indirectness/evaluation/runner.py \
  --method grade.indirectness.method_llm \
  --dataset benchmark/online_pipeline/grade/indirectness/datasets/grade_v3_lite/splits/smoke \
  --run-id indirectness-agentic-llm-smoke \
  --workers 1 \
  --batch-size 5 \
  --resume \
  --progress
```

Use dev for iteration:

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/grade/indirectness/evaluation/runner.py \
  --method grade.indirectness.method_llm \
  --dataset benchmark/online_pipeline/grade/indirectness/datasets/grade_v3_lite/splits/dev \
  --run-id indirectness-agentic-llm-dev \
  --workers 8 \
  --batch-size 4 \
  --resume \
  --progress
```

Run aggregate diagnostics:

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/grade/indirectness/evaluation/aggregate_diagnostics.py \
  benchmark/online_pipeline/grade/indirectness/runs/<run_id>
```

Run field completeness audit:

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/grade/indirectness/evaluation/field_audit.py \
  --dataset benchmark/online_pipeline/grade/indirectness/datasets/grade_v3_lite \
  --output benchmark/online_pipeline/grade/indirectness/datasets/grade_v3_lite/field_audit.json
```

Use test only after the dev iteration is frozen.

## Runner Features

`evaluation/runner.py` supports:

- `--workers` for instance-level parallelism
- `--batch-size` for method-level batch LLM adjudication when supported
- `--resume` for checkpoint recovery
- `--progress` for progress logging
- immediate append to `predictions.jsonl`
- `indirectness_traces.jsonl` for method debug summaries

It also supports single-domain method specs:

```text
grade.indirectness.method_llm
```

## Web / RAG Policy

Web search is not part of benchmark prediction. It is allowed for developers to
read official documentation, but not for method execution on benchmark rows.

Dynamic RAG is not part of the current benchmark method. If added later, it
should be a static official-guidance-only resource and must not contain review,
article, SoF, footnote, or benchmark gold data.
