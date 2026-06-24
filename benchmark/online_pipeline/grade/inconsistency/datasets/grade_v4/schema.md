# inconsistency dataset

- `instances.jsonl`: one aligned SoF row / one domain input record
- `gold.jsonl`: normalized domain downgrade judgement
- `shared/row_records.jsonl`: canonical SoF-row records used by this domain dataset
- Required prediction fields for evaluation: `instance_id`, `domain`, `judgement.downgraded`, `judgement.severity`, `judgement.levels`, `judgement.level_evaluable`
