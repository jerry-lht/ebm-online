# Q2CRBench Data Quality

Source dataset: `2024 KDIGO CKD`

## Generated Artifacts

- abstract_only examples: 16312
- evidence_profile examples: 13145
- manifest rows: 16321

## Notes

- `evidence_profile` examples use Q2CRBench paper/outcome evidence profiles and are not full text.
- Missing screened records for EAN/ACR remain dataset-level blockers and are not included in main examples.

## Quality Counts

- blockers: 2
- invalid_label: 0
- json_parse_errors: 0
- missing_clinical_question: 0
- missing_evidence_profile: 3176
- missing_label: 0
- missing_title_abstract: 9

## Dataset Blockers

- Q2CRBench screened records are missing for 2020 EAN Dementia.
- Q2CRBench screened records are missing for 2021 ACR RA.
