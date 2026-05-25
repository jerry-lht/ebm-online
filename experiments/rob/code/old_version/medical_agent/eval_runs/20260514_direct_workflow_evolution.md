# Direct Workflow Evolution Note

Date: 2026-05-14

## Why this iteration

The previous two-stage/hybrid workflow can lose detail during Stage 1 extraction and can fail or hang before domain judging. The new `direct` workflow matches the target contract:

`sr_pico + xml_content + risk_of_bias_domain -> risk_of_bias_judgement`

It judges each RoB domain directly from source excerpts and returns `support_text`, `support_context`, and a short audit rationale.

## Implemented changes

- Added `--mode direct` to `src/main.py` and `src/batch_eval.py`.
- Added direct domain prompt in `src/prompts.py`.
- Added `_judge_domain_direct` in `src/evaluator.py`.
- Added conservative direct-mode calibration for common RoB boundary errors:
  - randomization list vs actual random sequence generation
  - sequence generation vs allocation concealment
  - self-reported outcomes and participant masking
  - objective/device outcomes
  - LOCF/complete-case attrition edge cases
- Added transient provider error retry for 502/503/504-like failures in `src/batch_eval.py`.
- Added article-only scorable metrics to batch reports.

## Key runs

### Problem-sample sanity checks

Command:

```bash
python src/batch_eval.py --pmids 21680092,22454006,23641371,23886027,24830749,24991622 --mode direct --model gpt-5-mini --timeout 180 --domain-context-max-chars 9000 --max-tokens 4096 --reasoning-effort minimal --max-retries 0 --concurrency 3 --no-support-filter
```

Result after calibration: `27/30 = 90.0%`

Run directory: `eval_runs/20260514_134930`

### Support-filter validation set

Command:

```bash
python src/batch_eval.py --limit 100 --mode direct --model gpt-5-mini --timeout 180 --domain-context-max-chars 9000 --max-tokens 4096 --reasoning-effort minimal --max-retries 0 --concurrency 2
```

The support filter found 56 eligible studies; 52 completed due to provider 502s.

Result: `172/260 = 66.2%`

Article-observable result: `89/130 = 68.5%`

Run directory: `eval_runs/20260514_143305`

### No-support-filter 100-study pressure test

Command:

```bash
python src/batch_eval.py --limit 100 --mode direct --model gpt-5-mini --timeout 180 --domain-context-max-chars 9000 --max-tokens 4096 --reasoning-effort minimal --max-retries 0 --concurrency 2 --no-support-filter
```

Result: `294/500 = 58.8%`

Article-only scorable result: `87/131 = 66.4%`

Run directory: `eval_runs/20260514_144929`

## Interpretation

Direct mode is operationally better: no Stage 1 extraction bottleneck, no extraction compression, and 100/100 completed in the pressure test with concurrency 2.

Raw full-dataset accuracy remains limited because many ground-truth judgements rely on evidence not present in the XML input: author emails, protocols, registries, tables/figures, original trial reports, or review notes. The report now separates article-only scorable accuracy from raw accuracy.

Domain performance on the 100-study pressure test:

- Random sequence generation: `76/100`
- Allocation concealment: `73/100`
- Blinding participants/personnel: `55/100`
- Blinding outcome assessment: `49/100`
- Incomplete outcome data: `41/100`

The remaining hard domains are not mainly extraction failures anymore; they are evidence-availability and review-specific interpretation problems.

## Recommended next workflow

Use direct mode as the default article-only evaluator:

```bash
python src/batch_eval.py --limit 100 --mode direct --model gpt-5-mini --timeout 180 --domain-context-max-chars 9000 --max-tokens 4096 --reasoning-effort minimal --max-retries 0 --concurrency 2
```

For collaborator-facing evaluation, report both:

- raw accuracy
- article-only scorable accuracy

Next improvement should be an evidence-availability gate:

1. Detect whether the supplied XML contains enough evidence for each domain.
2. If not, output `requires_review_context` or route to a workflow that includes Cochrane characteristics/support text/protocol/registry/table extraction.
3. Only compare strict article-only predictions against article-observable ground truth.

