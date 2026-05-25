# Evolution note: blinding and attrition fixes

Date: 2026-05-13

## Problem observed in the 100-study run

The weakest domains were:

- Blinding participants/personnel: 56/100
- Blinding outcome assessment: 49/100
- Incomplete outcome data: 47/100

Log review showed that the low scores were not one single failure mode.

For outcome-assessment blinding, the deterministic calibration layer was too broad. It sometimes changed an originally cautious `Unclear` or `High` judgement into `Low` whenever it saw objective/device-like language, even when the same evidence also contained self-report, diary, pain, questionnaire, open-label, or not-blinded signals.

For participants/personnel blinding, many errors were caused by "All outcomes" aggregation. The model and GT often disagreed on whether lack of blinding could materially affect a mix of objective and subjective outcomes.

For incomplete outcome data, many GT rationales depend on flow diagrams, tables, supplements, review notes, or author correspondence that are not directly present in the parsed XML text.

## Code changes

Updated `src/evaluator.py`:

- Tightened outcome-assessment Low calibration.
- Added subjective-outcome guards: self-report, questionnaire, diary, pain, symptom, depression/anxiety, WOMAC/VAS, quality of life, behavioral outcomes.
- Added open/unmasked guards: open-label, not blinded, no blinding, blinding not possible, participants informed, research assistants aware.
- Objective/device/lab/registry calibration now only promotes to `Low risk` when subjective/open-label signals are absent.
- Self-report/open-label or self-report/unmasked evidence can promote to `High risk`.

Updated batch runner:

- Added `--max-retries` and defaulted SDK retries to `0` via `MAX_RETRIES`/constructor default.
- Added faster cancellation behavior for interrupted concurrent runs.
- Added timeout retry parameters. A timed-out study can be retried once with smaller extraction/domain contexts.
- Added report-level retry counts.
- Added extraction JSON salvage, so malformed Stage 1 JSON no longer fails the whole study when fields can be recovered.

## Targeted validation

Targeted run:

- Directory: `eval_runs/20260513_225542`
- Completed: 8/10 studies
- Accuracy: 28/40 (70.0%)

Compared with the 100-study run on completed overlapping studies:

Improvements:

- `21680092`, blinding participants/personnel: `Unclear -> High`, now matches GT High.
- `23641371`, blinding outcome assessment: `Low -> High`, now matches GT High.
- `24830749`, allocation concealment: `Low -> Unclear`, now matches GT Unclear.
- `24830749`, blinding outcome assessment: `Low -> High`, now matches GT High.

Remaining or new issues:

- Some domain labels still fluctuate run-to-run because the model is nondeterministic and sometimes emits malformed/truncated JSON.
- `22454006` and `18779465` exposed long-request timeout behavior; lowering extraction context to 8000 allowed `18779465` to complete, but `22454006` remained slow in this session.
- Broader 30-study revalidation was interrupted because the API was timing out frequently; results from that run should not be used as an accuracy baseline.

## Follow-up validation on 2026-05-14

Smoke test:

- PMIDs: `18779465`, `22454006`
- Command used short primary timeout and smaller retry contexts.
- Result: both studies completed, 7/10 (70.0%).

30-study unfiltered validation:

- Directory: `eval_runs/20260514_113616`
- Initial run completed 29/30, 85/145 (58.6%).
- The only failure was malformed Stage 1 extraction JSON for `19291323`.
- After extraction salvage, `19291323` completed as 3/5 in `eval_runs/20260514_114848`.
- Combined estimate: 30/30 completed, 88/150 (58.7%).

This 30-study set should be interpreted as a stability check, not a new performance claim. It is the first 30 unfiltered standard RoB studies and includes several cases where GT support is not present in the parsed XML.

## Recommended next run

For a stable rerun, use a moderate concurrency and keep retries disabled:

```bash
python src/batch_eval.py \
  --limit 100 \
  --mode hybrid \
  --model gpt-5-mini \
  --timeout 180 \
  --extraction-max-chars 9000 \
  --domain-context-max-chars 6000 \
  --retry-timeout 180 \
  --retry-extraction-max-chars 5000 \
  --retry-domain-context-max-chars 3000 \
  --max-tokens 4096 \
  --reasoning-effort minimal \
  --max-retries 0 \
  --concurrency 3 \
  --no-support-filter
```

If the API is slow, prefer rerunning failed PMIDs later rather than increasing concurrency.
