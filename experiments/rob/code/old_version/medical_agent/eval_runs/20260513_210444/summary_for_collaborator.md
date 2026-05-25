# 100-study RoB evaluation summary

Date: 2026-05-13

## Run setup

Command:

```bash
python src/batch_eval.py \
  --limit 100 \
  --mode hybrid \
  --model gpt-5-mini \
  --timeout 180 \
  --extraction-max-chars 12000 \
  --domain-context-max-chars 6000 \
  --max-tokens 4096 \
  --reasoning-effort minimal \
  --concurrency 4 \
  --no-support-filter
```

Notes:

- `--concurrency 4` evaluates four studies in parallel.
- `--no-support-filter` selects from all standard RoB studies, rather than only studies where ground-truth support text can be phrase-matched in the XML article text.
- The run completed 100/100 studies with no study-level failures.
- Reports include model evidence, support context, and label comparisons. They do not include hidden chain-of-thought.

## Results

- Overall accuracy: 298/500 (59.6%)
- Article-observable accuracy: 84/131 (64.1%)
- External/review-context GT domains: 20
- Unknown or non-text GT domains: 78

Domain accuracy:

- Random sequence generation: 75/100 (75.0%)
- Allocation concealment: 71/100 (71.0%)
- Blinding participants/personnel: 56/100 (56.0%)
- Blinding outcome assessment: 49/100 (49.0%)
- Incomplete outcome data: 47/100 (47.0%)

Main mismatch categories:

- Ground-truth support not found in article XML: 113
- Over-inference from sparse reporting: 48
- Under-called due to missing or underused evidence: 17
- External/review context needed: 8
- Blinding outcome-type or role confusion: 8
- Figure/table/supplement needed: 6

## Interpretation

This 100-study run is a broader stress test than the previous 20-study dev run. Because it disables the support-text phrase filter, it includes many studies where ground-truth rationales depend on review notes, author correspondence, figures/tables, supplements, or text not present in the parsed XML. The raw accuracy is therefore a conservative estimate for article-only evaluation.

The model is strongest on selection-bias domains, especially random sequence generation and allocation concealment. The main remaining weaknesses are outcome-specific judgement for blinding and incomplete outcome data, plus cases where the ground truth is not directly observable from the article XML.

Recommended next step: split future evaluation into `article-only` and `review-context` subsets, then evaluate outcome-specific blinding/attrition before aggregating to "All outcomes".

