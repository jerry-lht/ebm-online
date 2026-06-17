# GRADE Benchmark v2

This benchmark uses SoF rows as the sample unit.

## Files

- `benchmark_core.jsonl`: default evaluation split.
- `benchmark_core_with_subgroup.jsonl`: subset with subgroup estimates for inconsistency-heavy evaluation.
- `benchmark_extended_gold.jsonl`: broader gold set for coverage and analysis.
- `excluded_audit.jsonl`: excluded samples and reasons.

## Scoring

Default scoring uses `overall_certainty` plus the four scored GRADE domains:
`risk_of_bias`, `inconsistency`, `indirectness`, and `imprecision`.
Publication bias is retained in gold but not scored by default.
`levels="unclear"` means the source supports a domain downgrade but does not allocate a specific level to that domain.
Level metrics should skip rows where `level_evaluable=false`.

## LLM Configuration

- config path: `/Users/jerry/Documents/code/medical/EBM-Online/sr-cleaned/code/benchmark.local.json`
- config hash: `72072303891090fcde99010c0da4ac7d75da7b4171861a2de3024388b6cb0d88`
- model: `gpt-5.4-mini`
- base_url: `https://tokenrun.org/v1`
- used for calls: `False`

The API key is only read from the config file at build time and is never written to outputs.

## Sample Format

Each row has `sample_id`, `review`, `input`, `gold`, `input_coverage`, and `audit`.
