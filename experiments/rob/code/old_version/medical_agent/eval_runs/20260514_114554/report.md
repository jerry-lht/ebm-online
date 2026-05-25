# Batch Risk of Bias Eval Report

This report contains an audit trace: explicit extracted evidence, model-provided rationales, and label comparisons. It does not include hidden chain-of-thought.

- Studies: 0
- Domains: 0
- Accuracy: 0/0 (0.0%)
- Article-observable accuracy: 0/0 (0.0%)
- External/review-context GT domains: 0
- Unknown or non-text GT domains: 0
- Timeout retries recovered: 0

## Summary

| PMID | Study | Correct | Accuracy | Seconds | Retry |
|---|---|---:|---:|---:|---|

## Error Types

- No mismatches.
## Workflow Evolution Notes

- Inspect mismatches where prediction is `Unclear risk` but GT is `Low risk`: these usually mean retrieval or Stage 1 extraction missed a concrete methodological phrase.
- Inspect mismatches where prediction is `Low risk` or `High risk` but GT is `Unclear risk`: these usually mean the prompt is allowing too much inference from generic trial language.
- For blinding mismatches, add outcome-type cues to the prompt: self-report outcomes, objective outcomes, assessor-administered outcomes, and whether lack of blinding can materially affect the outcome.
- For allocation concealment mismatches, require the model to distinguish sequence generation from concealment before assignment.