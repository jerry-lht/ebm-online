# Target-domain workflow evolution

Goal: improve low-performing RoB domains without overfitting to individual PMIDs:

- Blinding of outcome assessment
- Incomplete outcome data

Dataset slice used for rapid iteration:

- `rob_core_dataset` first 20 PMIDs
- Same PMIDs as `eval_runs/20260514_183251`
- Model: `gpt-5-mini`

## Experiments

| Workflow | Overall | Blinding outcome assessment | Incomplete outcome data | Notes |
|---|---:|---:|---:|---|
| `direct` baseline | 62/100 = 62% | 12/20 = 60% | 9/20 = 45% | Best rapid-iteration baseline |
| `targeted` v1 | 54/100 = 54% | 12/20 = 60% | 6/20 = 30% | Evidence map judged directly; attrition became too conservative |
| `targeted` v2 | 57/100 = 57% | 12/20 = 60% | 5/20 = 25% | Softer attrition prompt still over-called Unclear |
| `evidence` | 42/100 = 42% | 6/20 = 30% | 5/20 = 25% | Global evidence-table compression loses too much detail |
| `direct` with 16k context | 56/100 = 56% | 12/20 = 60% | 8/20 = 40% | More context adds noise; retrieval is not solved by bigger windows |
| `audited` | 61/100 = 61% | 11/20 = 55% | 9/20 = 45% | Direct primary + evidence-map guardrails; close, but not better |

## Decision

Keep `direct` as the recommended main workflow for now.

The experimental `targeted` and `audited` modes are kept in code for future
analysis, but they should not be reported as the main benchmark unless later
runs beat `direct` on a held-out slice.

## Interpretation

The failed improvements are informative:

- A single evidence-map prompt makes incomplete outcome data too conservative.
- A global evidence table compresses away the exact details needed for RoB 1.0.
- Larger domain context windows do not reliably help; they add distracting text.
- Evidence-map guardrails can fix individual cases but also introduce new errors.

The remaining bottleneck is likely not a simple prompt/workflow shape. The hard
cases need better article-to-GT observability handling and possibly a specialized
numeric/table parser for attrition and CONSORT flow details.

## Current best 100-study result

Best current main result remains:

- Run: `eval_runs/20260514_core100_optimized`
- Dataset: `rob_core_dataset` first 100
- Overall: 294/500 = 58.8%
- Article-only subset: 247/405 = 61.0%

Domain results on `rob_core_dataset` first 100:

| Domain | Accuracy |
|---|---:|
| Random sequence generation | 80/100 = 80.0% |
| Allocation concealment | 69/100 = 69.0% |
| Blinding participants/personnel | 57/100 = 57.0% |
| Blinding outcome assessment | 48/100 = 48.0% |
| Incomplete outcome data | 40/100 = 40.0% |

