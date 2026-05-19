# Question -> PICO Implementation Plan

## Summary

This experiment line is a new task and must stay fully separate from the existing `Abstract -> PICO` extraction workflow in `pico-exp`.

The task is:

- dataset: `Q2CRBench-3 / Clinical_Questions`
- input: clinical question text
- output: structured `P / I / C / O` slots
- format: non-extractive slot filling, not token/span extraction
- prompting strategy: split extraction by label, then aggregate
- evaluation: slot-text matching plus an LLM rubric
- result isolation: independent outputs, metrics, and tables under `q2pico-exp`

The implementation goal is to preserve the design discipline already used in `pico-exp`:

- reproducible prepared data artifacts
- explicit prompt versions
- run configs saved with each run
- validator/evaluator/judge as separate steps
- table outputs that are append-only by run key

## Task Contract

### Input Contract

Each example comes from `Q2CRBench-3/Clinical_Questions` and contains:

- `Question`
- `P`
- `I`
- `C`
- `O`
- optional metadata such as `Index`, `Aspect`, `Dataset`, `S`

The runtime input is only the clinical question text, not evidence abstracts.

### Output Contract

The model output is a normalized structured slot object with four fields:

```json
{
  "P": ["..."],
  "I": ["..."],
  "C": ["..."],
  "O": ["..."]
}
```

Internal single-label prompt responses should use keyed JSON payloads:

- `P`: `{"participants": [...]}`
- `I`: `{"interventions": [...]}`
- `C`: `{"comparators": [...]}`
- `O`: `{"outcomes": [...]}`

Aggregation converts those keyed payloads into the canonical `P/I/C/O` slot object.

### Non-goals

This v1 does not do:

- extractive span offsets
- token-level BIO labels
- `S` slot extraction
- shared result tables with `Abstract -> PICO`
- mixed evaluation with EBM-NLP span metrics

## Directory Layout

All new artifacts should live in `q2pico-exp` and stay independent from `pico-exp`.

Recommended structure:

```text
q2pico-exp/
  code/
    q2pico/
      __init__.py
      schemas.py
      io_utils.py
      config.py
      prompt_registry.py
      question_data.py
      slot_validate.py
      slot_evaluate.py
      judge_evaluate.py
      cli/
        __init__.py
        prepare_data.py
        run_llm.py
        validate_predictions.py
        evaluate_predictions.py
        evaluate_llm_judge.py
      prompts/
        stage_slot_split_v1/
          few_shot_question_slot_split_v1_p_only.txt
          few_shot_question_slot_split_v1_i_only.txt
          few_shot_question_slot_split_v1_c_only.txt
          few_shot_question_slot_split_v1_o_only.txt
        stage_rubric/
          judge_question_rubric_v1.txt
    tests/
      test_question_data.py
      test_run_llm.py
      test_slot_validate.py
      test_slot_evaluate.py
      test_judge_evaluate.py
  data/
    Q2CRBench-3/
  results/
    data/
    preds/
    metrics/
    reports/
    tables/
```

If shared utilities from `pico-exp` are copied or adapted, they should be intentionally duplicated or lightly vendored into `q2pico` rather than creating hidden cross-experiment coupling.

## Data Model

### Core Schema

Define a dedicated example schema instead of reusing `DocumentExample`.

Suggested dataclass:

```python
@dataclass
class QuestionPICOExample:
    question_id: str
    split: str
    question_text: str
    gold_slots: dict[str, list[str]]
    metadata: dict[str, Any] = field(default_factory=dict)
```

Required invariants:

- `gold_slots` must always contain exactly `P`, `I`, `C`, `O`
- each slot value is a string list
- blank strings are removed
- duplicate values are removed conservatively after whitespace trim
- original text is preserved for reporting
- normalized text is derived in evaluators, not stored as a replacement for original text

### Metadata

Store at least:

- `source_dataset`
- `source_index`
- `aspect`
- original `S`
- raw source row snapshot or source row identifiers
- split manifest version

## Data Preparation

### Source Loader

Add a loader for `Clinical_Questions` parquet.

Responsibilities:

- read parquet rows from `data/Q2CRBench-3/Clinical_Questions/*.parquet`
- map source columns into `QuestionPICOExample`
- convert scalar `P/I/O` into lists
- preserve `C` as list if already multi-valued
- normalize nulls to empty lists

### Split Strategy

Lock the first split manifest in repo outputs and do not allow ad hoc reshuffling during experiments.

Default split:

- `fewshot20`
- `dev20`
- `test59`

Requirements:

- deterministic seed: `20260516`
- stratify as much as possible by `Dataset`
- save exact question ids in manifest
- downstream CLIs consume prepared split files, not raw parquet

### Prepared Outputs

Write:

- `results/data/questions.full.examples.jsonl`
- `results/data/questions.fewshot20.examples.jsonl`
- `results/data/questions.dev20.examples.jsonl`
- `results/data/questions.test59.examples.jsonl`
- `results/data/manifests/question_split_v1.json`
- `results/tables/dataset_summary.csv`
- `results/tables/question_split_summary.csv`

`dataset_summary.csv` for this experiment should describe:

- total examples
- per-source-dataset counts
- per-split counts
- slot non-empty rates for `P/I/C/O`

## Prompting Strategy

### Split-by-label Extraction

Use a four-pass label-split extraction strategy analogous to the best-of-split design in `pico-exp`, but adapted for slot filling.

Per label:

- `P`: ask for participant/population slot
- `I`: ask for intervention slot
- `C`: ask for comparator/control slot
- `O`: ask for outcome slot

The prompts should explicitly say:

- use only information inferable from the question
- return concise slot values
- do not invent evidence details absent from the question
- return JSON only

Because this task is non-extractive, prompts should not require exact substring copying.

### Few-shot Selection

Few-shot examples come only from `fewshot20`.

Rules:

- no few-shot leakage from `dev20` or `test59`
- record chosen shot ids in every `run_config.json`
- allow per-label few-shot files if later ablations want label-specialized exemplars

### Prompt Versioning

Lock prompt versions in run metadata:

- `question_slot_split_v1_p_only`
- `question_slot_split_v1_i_only`
- `question_slot_split_v1_c_only`
- `question_slot_split_v1_o_only`
- `judge_question_rubric_v1`

## Runtime Pipeline

### Inference CLI

Implement a dedicated `run_llm` CLI for question slot extraction.

Inputs:

- prepared examples JSONL
- provider config
- model id
- output dir
- prompt mode
- few-shot examples
- workers
- resume

Outputs:

- `prompts.jsonl`
- `raw.jsonl`
- `errors.jsonl`
- `run_config.json`
- when split mode is used, subdirectories `labels/P`, `labels/I`, `labels/C`, `labels/O`

### Run Metadata

Every run config must store:

- `task = "question_pico"`
- `task_version = "q2crbench_question_v1"`
- `input_type = "clinical_question"`
- `provider`
- `model_id`
- `model_version`
- `base_url`
- `api_mode`
- `prompt_mode`
- `prompt_version`
- `label_prompt_versions`
- `label_few_shot_paths`
- `few_shot_doc_ids`
- `split_manifest_path`
- `examples_path`
- `workers`
- `timeout_seconds`
- `max_retries`
- `resume`
- `created_at`

### Aggregation

The top-level aggregated prediction for each question should be one row with:

```json
{
  "question_id": "...",
  "response": "{\"P\": [...], \"I\": [...], \"C\": [...], \"O\": [...]}"
}
```

Per-label raw outputs remain in subdirectories for debugging and ablations.

## Validation

### Validator Responsibilities

Add a dedicated slot validator, not a span validator.

Checks:

- raw row has `question_id` and JSON string `response`
- parsed object is a dict
- only allowed top-level keys: `P`, `I`, `C`, `O` or expected keyed single-label payload before aggregation
- each slot value is a list of strings
- empty strings removed
- duplicates removed after conservative normalization

Metrics:

- `invalid_json_rate`
- `schema_invalid_rate`
- `non_list_slot_rate`
- `non_string_item_rate`
- `duplicate_value_rate`
- `empty_value_rate`
- `raw_rows`
- `response_items`
- `written_values`

Validator outputs:

- `validated.slots.jsonl`
- `quality.json`
- append-only `results/tables/llm_quality.csv`

## Evaluation

### Main Evaluator

Add a text-slot evaluator dedicated to `P/I/C/O`.

Core metrics:

- `slot_exact_micro_f1`
- `slot_normalized_micro_f1`
- per-label exact F1 for `P/I/C/O`
- per-label normalized F1 for `P/I/C/O`
- `pico_complete_question_rate`
- per-label complete question rate

Normalization policy:

- strip
- casefold
- collapse whitespace
- normalize common dash variants

No stemming, synonym expansion, or ontology mapping in v1.

### Completeness

A label is complete for a question when every distinct normalized gold value for that label appears in prediction.

A full-question complete hit requires all non-empty gold labels among `P/I/C/O` to be complete.

### Evaluation Outputs

Write:

- `results/metrics/<run>.slot_metrics.json`
- `results/tables/llm_slot_f1.csv`
- `results/tables/llm_slot_completeness.csv`
- `results/tables/run_index.csv`

The `run_index.csv` here is question-task local and must not be merged with `pico-exp` run tables.

## LLM Rubric Judge

### Purpose

Use a question-specific rubric to evaluate semantic adequacy beyond literal string matching.

The judge prompt should see only:

- question text
- gold `P/I/C/O`
- predicted `P/I/C/O`

It should not reference abstracts or evidence documents.

### Rubric Dimensions

Keep the same reporting frame as the abstract task for comparability of judging style:

- `completeness`
- `accuracy`
- `noise`
- `granularity`
- `overall_verdict`

Apply them per label and overall.

### Judge Outputs

Write:

- `judge.jsonl`
- `judge_metrics.json`
- `results/tables/llm_judge_overall.csv`
- `results/tables/llm_judge_per_label.csv`

The question-task judge evaluator version should be independent from the abstract-task judge version.

## Results Isolation

Do not share result tables with `pico-exp`.

All outputs in this experiment should remain under `q2pico-exp/results/...`.

Recommended naming:

- predictions: `results/preds/llm/<setting>/...`
- metrics: `results/metrics/<setting>.*.json`
- tables: `results/tables/*.csv`
- reports: `results/reports/*.md` or `.json`

Suggested `setting` naming convention:

- `question_slot_split_v1_dev20`
- `question_slot_split_v1_test59`
- `question_slot_split_v1_ablation_<name>`

## Test Plan

### Data Tests

Add tests for:

- parquet row to `QuestionPICOExample`
- null handling
- comparator multi-value handling
- deterministic split manifest generation
- split sizes `20 / 20 / 59`

### Runtime Tests

Add tests for:

- prompt rendering uses `question_text`
- split-label runs create `P/I/C/O` label subdirectories
- top-level aggregation writes one merged slot object per question
- resume skips completed label subrequests only
- `run_config.json` records `task`, split manifest, prompt versions, and few-shot ids

### Validator Tests

Add tests for:

- invalid JSON
- non-dict payload
- missing slot keys
- unknown slot keys
- non-list slot values
- non-string items
- deduplication and whitespace trimming

### Evaluator Tests

Add tests for:

- exact vs normalized matching
- per-label F1 with `C` included
- full-question completeness
- partial-question completeness
- isolated question-task table writes

### Judge Tests

Add tests for:

- judge payload construction from question examples
- question rubric parsing and normalization
- table outputs
- resume behavior

### Non-regression Tests

Run the existing `pico-exp` test subsets that cover:

- prompt registry
- `run_llm`
- validator
- text evaluator
- judge evaluator

The acceptance condition is zero behavior change in the abstract experiment.

## Acceptance Criteria

The implementation is complete when:

1. raw `Clinical_Questions` parquet can be converted into reproducible prepared splits
2. a four-label question-slot LLM run can be executed end to end
3. validated slot outputs are saved with quality metrics
4. slot metrics and rubric metrics are written into question-local tables
5. all Question->PICO tests pass
6. existing `Abstract -> PICO` tests continue to pass unchanged

## Initial Milestones

Recommended implementation order:

1. create `q2pico` schemas, I/O, prompt registry, and data loader
2. implement `prepare_data` and fixed split manifest generation
3. implement question `run_llm` with split-label aggregation
4. implement slot validator and evaluator
5. implement question rubric judge
6. add tests and run focused test subsets

## Default Assumptions

Unless changed later, v1 assumes:

- comparator is first-class and stays separate from intervention
- all scoring is text-slot based, not ontology based
- no shared code dependency back into `pico-exp` is required for correctness
- no mixed summary table across abstract and question tasks will be produced
- prompt iteration uses `dev20`; final reported comparison uses locked `test59`
