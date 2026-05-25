# RoB 5-Domain Extraction

LLM-based risk-of-bias assessment for RCTs included in Cochrane systematic
reviews. For each study, five independent API calls produce one judgement
per RoB 1.0 domain.

## Domains

| # | Domain | Bias type | Judgement is driven by ... |
|---|---|---|---|
| 1 | Random sequence generation | Selection bias | Method described in the article |
| 2 | Allocation concealment | Selection bias | Concealment mechanism described in the article |
| 3 | Blinding of participants and personnel | Performance bias | Blinding status + outcome subjectivity |
| 4 | Blinding of outcome assessment | Detection bias | Assessor blinding + outcome subjectivity (worst-outcome rule) |
| 5 | Incomplete outcome data | Attrition bias | Reported per-arm loss numbers and reasons |

Selective reporting and "Other bias" are not assessed in this pipeline.

## Inputs

Each study record under `rob_cleaned_dataset/<pmid>.json` provides three input
fields to the LLM:

- `review_title` — title of the parent systematic review
- `sr_pico` — population / intervention / comparison / outcome of the parent SR
- `xml_content` — article sections (Abstract / Methods / Results / Discussion)
  and tables in raw JATS XML

Other dataset fields (`risk_of_bias`, `characteristics`) are kept for
evaluation but are NOT provided to the model at prediction time.

## Output

For each study, `results/predictions/<pmid>.json` contains:

```json
{
  "study_id": "Ross 2004",
  "pmid": "15249261",
  "model": "gpt-5.4-mini",
  "prediction": {
    "risk_of_bias": [
      {"domain": "Random sequence generation (selection bias)",
       "judgement": "Low risk | High risk | Unclear risk",
       "support_text": "Quote: ... Comment: ...",
       "source": "source_full_text | source_review_characteristics | ..."},
      ...
    ]
  },
  "slot_map": {"random_sequence_generation": "Low risk", ...}
}
```

## File layout

```
experiments/rob/
├── domain_specs.py        # Per-domain criteria and the meta-principle prompt
├── run_experiment.py      # 5-domain prediction pipeline
├── evaluate.py            # 3-class or binary (High vs Not-high) scoring
├── clean_dataset.py       # Drop dataset records that have empty input fields
├── rob_cleaned_dataset/   # Source dataset (one file per PMID)
├── results/
│   ├── predictions/       # Model predictions
│   └── evaluation/        # CSVs + confusion matrices
└── code/old_version/      # Archived prior iterations (baseline / v3 / v4 / v5 / etc.)
```

## Usage

### Predict

```bash
python run_experiment.py                          # all studies in dataset
python run_experiment.py --max_studies 20         # quick test slice
python run_experiment.py --resume                 # skip files already in results/predictions/
python run_experiment.py --concurrency 5          # parallel studies
python run_experiment.py --model gpt-4o-mini      # alternative model
python run_experiment.py --two_stage              # see "Two-stage extraction" below
```

Single-stage mode issues 5 parallel API calls per study (one per domain).
Concurrency `N` keeps roughly `5N` calls in flight at peak.

### Two-stage extraction

`--two_stage` splits each domain into two calls:

1. **Stage 1 — extraction.** The model fills a per-domain JSON schema from
   the article: verbatim quotes, structured numbers (per-arm `randomised`,
   `analysed`, `lost`), boolean threshold flags, and a self-suggested
   judgement based only on the extracted facts.
2. **Stage 2 — judgement.** The model receives the stage-1 JSON plus the
   article and produces the final judgement. The stage-2 prompt instructs
   the model to defer to the extracted numbers whenever a numerically
   defined threshold is satisfied, rather than re-arguing from the
   article's narrative.

Per-domain extraction schemas live in `domain_specs.py` (`_RANDOM_SEQUENCE_SCHEMA`,
`_ALLOCATION_CONCEALMENT_SCHEMA`, etc.). The stage-1 JSON is stored under
`_evidence` in each prediction record so failures are debuggable.

API cost doubles (10 calls per study). See "Two-stage results vs limits"
below before deciding to use it for a full run.

### Evaluate

```bash
python evaluate.py                  # 3-class: Low / High / Unclear, micro-accuracy per domain
python evaluate.py --binary         # collapse Low+Unclear into "Not high"; report High-risk precision/recall/F1
```

Outputs go to `results/evaluation/`:

- `domain_accuracy.csv` / `domain_accuracy_binary.csv` — per-domain summary
- `per_study_results.csv` / `per_study_results_binary.csv` — one row per (study, domain)
- `confusion_matrices.txt` / `confusion_matrices_binary.txt` — per-domain GT × pred grid

### Clean dataset

`clean_dataset.py` deletes dataset files (and their predictions) where any
required input field is empty. Required = all four `sr_pico` keys plus
`characteristics.{participants,interventions,outcomes,notes}`.

```bash
python clean_dataset.py --dry_run --show_reasons   # preview
python clean_dataset.py                            # delete (also drops matching predictions)
python clean_dataset.py --no_predictions           # keep predictions; only touch dataset
```

## Prompt design

Each domain has its own `criteria` block in `domain_specs.py`. The five
domains are decoupled — each runs as an independent API call with its own
system prompt — so calibration can differ by domain.

### Meta-principle (applied to all domains)

The system prompt includes one shared principle:

> **High risk requires positive evidence, not absence of evidence.**
> If the article does not describe the relevant procedure (randomisation
> method, concealment mechanism, blinding status, attrition numbers), the
> correct judgement is **Unclear**, not High.

This is the single most important rule across the pipeline because the
default failure mode of an LLM grader is to over-call High whenever it sees
"missing information" as suspicious. The meta-principle anchors every domain
on the same rule.

### Per-domain stance

| Domain | Default direction | Why |
|---|---|---|
| Random sequence | Permissive on Low | Most published RCTs use a proper random method; "computer-generated" / "block randomisation" / "central randomisation" are reliable Low-risk signals. |
| Allocation concealment | Strict on Low | Most papers do not describe concealment; "Default Unclear" is correct. Only an explicit concealment mechanism (central allocation, SNOSE, identical containers) earns Low. |
| Blinding (participants) | Outcome-aware | Unblinded + objective outcomes can still be Low (e.g. all-cause mortality). Unblinded + subjective outcomes is High. |
| Blinding (outcome assessment) | Worst-outcome rule | If a study mixes objective and subjective outcomes and the subjective ones are unblinded → High. Do not average detection bias across the outcome set. |
| Incomplete outcome | Numbers-or-Unclear | High requires reported numbers crossing thresholds (≥30% total loss on the analysed outcome, ≥10 pp differential). When CONSORT / per-arm analysed numbers are missing, Unclear is the correct call — not High. |

### Why decoupled criteria

The five domains have very different evidence structures:

- Selection-bias domains (1 & 2) hinge on a description of the randomisation
  procedure that is either present or not.
- Performance / detection bias (3 & 4) require reasoning about outcome type
  in addition to blinding status.
- Attrition bias (5) requires arithmetic on per-arm flow numbers.

Forcing one prompt to handle all five flattens the rules and produces either
over-calling Unclear (too strict) or over-calling High (too aggressive).
Independent prompts per domain let each calibration match its domain's
evidence shape. They are also independent at inference time — the 5 calls
share the same `user_evidence` block but no other state.

## Two-stage results vs limits

On a 100-study slice, two-stage extraction did **not** produce a broad gain.
It improved some blinding behaviour but did not solve the hardest recall
problem in attrition bias:

| Domain | Single-stage F1 | Two-stage F1 | Main observation |
|---|---:|---:|---|
| Random sequence | 0.50 | 0.50 | No change; High cases are very rare in this slice. |
| Allocation concealment | 0.00 | 0.00 | Still fails to find rare High cases. |
| Blinding participants/personnel | 0.50 | ~0.53-0.61 | Sometimes improves because extraction forces outcome categorisation. |
| Blinding outcome assessment | 0.54 | ~0.50-0.51 | Mixed; worst-outcome rule helps, but false positives remain. |
| Incomplete outcome data | 0.29 | ~0.19-0.24 | Worse or similar; stage-1 often extracts the wrong attrition denominator/time point. |

The main bottleneck is **not** stage-2 judgement. After adding
`suggested_judgement` and threshold flags to stage-1, stage-2 usually follows
stage-1. The remaining failures are mostly in stage-1 extraction itself:

- It picks the wrong time point (e.g. baseline table or early follow-up instead
  of the analysed outcome horizon).
- It treats treatment discontinuation, questionnaire response, or a study
  sub-design as the analysed outcome denominator.
- It misses CONSORT-style flow details when they are in complex tables.
- It cannot recover attrition judgements that Cochrane reviewers made from
  information not present in the supplied article text.

Because of this, more prompt tuning has diminishing returns for incomplete
outcome data. A real improvement probably requires either a stronger model for
stage-1 extraction or a purpose-built CONSORT/table parser that provides
verified per-arm flow numbers before the LLM judges RoB.

## Evaluation notes

- Ground truth is parsed from each study's `risk_of_bias` array. When a paper
  has multiple GT entries for the same domain (e.g. "objective outcomes:
  Low" + "patient-reported outcomes: High"), they are merged into a single
  worst-case judgement (High > Unclear > Low) before scoring. This matches
  the worst-outcome rule used in the Blinding-outcome prompt.
- The "Blinding (performance bias and detection bias)" merged GT entry maps
  to BOTH blinding domains during scoring.
- API non-determinism: even with `temperature=0`, repeated runs of the same
  prompts vary by ≈±2% per domain on a 100-study slice. Differences smaller
  than that on a single run are noise.
- In binary mode, accuracy is dominated by class imbalance (most domains
  have <30% High prevalence). Use precision / recall / F1 — not accuracy —
  to compare runs.

## Credits

The dataset is derived from Cochrane systematic reviews; ground-truth RoB
judgements are the original Cochrane reviewers'. Prior iterations of the
pipeline (data prep, multi-stage extraction, single-step variants) live in
`code/old_version/`.
