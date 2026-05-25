# Full Eval Error Analysis

Run: `eval_runs/full_eval/20260516_152125`

- Completed studies: 346/346
- Domains: 1730
- Raw accuracy: 973/1730 (56.2%)

## Domain Summary

| Domain | Accuracy | Majority baseline | GT distribution | Pred distribution |
|---|---:|---:|---|---|
| random sequence generation | 267/346 (77.2%) | Low risk: 245/346 (70.8%) | Low risk:245, Unclear risk:91, High risk:10 | Low risk:197, Unclear risk:143, High risk:6 |
| allocation concealment | 247/346 (71.4%) | Low risk: 169/346 (48.8%) | Low risk:169, Unclear risk:163, High risk:14 | Unclear risk:187, Low risk:151, High risk:8 |
| blinding of participants and personnel | 174/346 (50.3%) | High risk: 154/346 (44.5%) | High risk:154, Unclear risk:98, Low risk:94 | High risk:144, Low risk:117, Unclear risk:85 |
| blinding of outcome assessment | 129/346 (37.3%) | Low risk: 170/346 (49.1%) | Low risk:170, High risk:109, Unclear risk:67 | Unclear risk:175, Low risk:111, High risk:60 |
| incomplete outcome data | 156/346 (45.1%) | Low risk: 205/346 (59.2%) | Low risk:205, Unclear risk:74, High risk:67 | Low risk:173, Unclear risk:146, High risk:27 |

## Main Failure Pattern

The two weakest domains are below or near simple label-prior baselines:

- `blinding of outcome assessment`: model 129/346 (37.3%), majority `Low risk` baseline 170/346 (49.1%), predictions {'Unclear risk': 175, 'Low risk': 111, 'High risk': 60}
- `incomplete outcome data`: model 156/346 (45.1%), majority `Low risk` baseline 205/346 (59.2%), predictions {'Unclear risk': 146, 'Low risk': 173, 'High risk': 27}

## Confusion Matrices

### random sequence generation

| GT -> Pred | Count |
|---|---:|
| Low risk -> Unclear risk | 60 |
| Unclear risk -> Low risk | 13 |
| High risk -> Unclear risk | 5 |
| Low risk -> High risk | 1 |

### allocation concealment

| GT -> Pred | Count |
|---|---:|
| Low risk -> Unclear risk | 53 |
| Unclear risk -> Low risk | 32 |
| High risk -> Unclear risk | 7 |
| Unclear risk -> High risk | 4 |
| High risk -> Low risk | 3 |

### blinding of participants and personnel

| GT -> Pred | Count |
|---|---:|
| Unclear risk -> High risk | 43 |
| High risk -> Unclear risk | 38 |
| High risk -> Low risk | 29 |
| Unclear risk -> Low risk | 28 |
| Low risk -> Unclear risk | 20 |
| Low risk -> High risk | 14 |

### blinding of outcome assessment

| GT -> Pred | Count |
|---|---:|
| Low risk -> Unclear risk | 80 |
| High risk -> Unclear risk | 61 |
| High risk -> Low risk | 23 |
| Low risk -> High risk | 20 |
| Unclear risk -> Low risk | 18 |
| Unclear risk -> High risk | 15 |

### incomplete outcome data

| GT -> Pred | Count |
|---|---:|
| Low risk -> Unclear risk | 77 |
| High risk -> Unclear risk | 34 |
| Unclear risk -> Low risk | 33 |
| High risk -> Low risk | 26 |
| Low risk -> High risk | 14 |
| Unclear risk -> High risk | 6 |

## Error Types

| Error type | Count |
|---|---:|
| gt_support_not_found_in_article_text | 452 |
| under-called_due_to_missing_or_underused_evidence | 127 |
| over-inferred_from_sparse_reporting | 117 |
| blinding_outcome_type_or_role_confusion | 29 |
| figure_table_or_supplement_needed | 21 |
| attrition_balance_or_missing_data_handling | 9 |
| allocation_concealment_detail_threshold | 1 |
| criteria_application_mismatch | 1 |

## Threshold Calibration Simulation

This is diagnostic only. It does not prove a valid held-out improvement, but it shows where the headroom is.

| Setting | Split | Accuracy | Blinding outcome assessment | Incomplete outcome data |
|---|---|---:|---:|---:|
| baseline direct | test half | 463/865 (53.5%) | 58/173 (33.5%) | 66/173 (38.2%) |
| baseline direct | full run | 973/1730 (56.2%) | 129/346 (37.3%) | 156/346 (45.1%) |
| flip target Unclear->Low | test half | 520/865 (60.1%) | 88/173 (50.9%) | 93/173 (53.8%) |
| flip target Unclear->Low | full run | 1061/1730 (61.3%) | 175/346 (50.6%) | 198/346 (57.2%) |
| target domains always Low | test half | 520/865 (60.1%) | 84/173 (48.6%) | 97/173 (56.1%) |
| target domains always Low | full run | 1063/1730 (61.4%) | 170/346 (49.1%) | 205/346 (59.2%) |

Interpretation: a very blunt threshold change crosses 60% on the second half and full run, because many GT labels for outcome assessment and attrition are `Low risk` while the model predicts `Unclear risk`. This would improve exact-match accuracy but must be framed as threshold calibration, not better evidence understanding.

## Lowest Review Groups

| Accuracy | Studies | Score distribution | Review title |
|---:|---:|---|---|
| 7/20 (35.0%) | 4 | {2: 3, 1: 1} | Conservative, physical and surgical interventions for managing faecal incontinence and constipation in adults with central neurological diseases |
| 19/45 (42.2%) | 9 | {3: 3, 1: 4, 2: 1, 4: 1} | Immunomodulators and immunosuppressants for relapsing‐remitting multiple sclerosis: a network meta‐analysis |
| 22/50 (44.0%) | 10 | {1: 3, 3: 4, 2: 1, 5: 1, 0: 1} | Digital tracking, provider decision support systems, and targeted client communication via mobile devices to improve primary health care |
| 22/50 (44.0%) | 10 | {1: 1, 3: 3, 2: 6} | Interventions for increasing fruit and vegetable consumption in children aged five years and under |
| 9/20 (45.0%) | 4 | {3: 2, 1: 1, 2: 1} | Non‐invasive high‐frequency ventilation in newborn infants with respiratory distress |
| 9/20 (45.0%) | 4 | {3: 2, 2: 1, 1: 1} | Non‐pharmacological interventions for the prevention of pain during endotracheal suctioning in ventilated neonates |
| 14/30 (46.7%) | 6 | {2: 2, 1: 1, 3: 3} | Interventions to improve return to work in depressed people |
| 12/25 (48.0%) | 5 | {3: 3, 2: 1, 1: 1} | Shared decision‐making interventions for people with mental health conditions |
| 10/20 (50.0%) | 4 | {3: 3, 1: 1} | Early developmental intervention programmes provided post hospital discharge to prevent motor and cognitive impairment in preterm infants |
| 110/200 (55.0%) | 40 | {3: 14, 4: 10, 1: 4, 2: 12} | Decision aids for people facing health treatment or screening decisions |
| 67/120 (55.8%) | 24 | {1: 3, 5: 2, 4: 5, 3: 8, 2: 5, 0: 1} | Meditation for the primary and secondary prevention of cardiovascular disease |
| 12/20 (60.0%) | 4 | {3: 2, 4: 1, 2: 1} | Combined oral contraceptive pill for primary dysmenorrhoea |
| 21/35 (60.0%) | 7 | {3: 3, 4: 2, 2: 2} | Polyunsaturated fatty acids (PUFA) for attention deficit hyperactivity disorder (ADHD) in children and adolescents |
| 84/140 (60.0%) | 28 | {4: 9, 1: 2, 2: 6, 3: 8, 5: 2, 0: 1} | Exercise for osteoarthritis of the knee |
| 22/35 (62.9%) | 7 | {5: 2, 3: 1, 4: 1, 2: 2, 1: 1} | Initial arch wires used in orthodontic treatment with fixed appliances |

## Study Score Distribution

`{0: 9, 1: 35, 2: 84, 3: 121, 4: 78, 5: 19}`

Lowest examples:

- 30948606 Echevarria 2018: 0/5
- 32267989 Rigoard 2019: 0/5
- 32878061 Sokal 2020: 0/5
- 32887850 Schlenk 2020: 0/5
- 33428638 Chumachenko 2021: 0/5
- 33627312 Mittra 2021: 0/5
- 35413873 Ruff 2022: 0/5
- 35835476 Patil 2022: 0/5
- PMC4208703 GALALZ3005 Hager 2014: 0/5
- 14647140 Clayton 2007: 1/5
- 19209172 Vodermaier 2009: 1/5
- 19798037 Nidich 2009: 1/5
- 21342490 Freeman 2011: 1/5
- 22697448 McCabe 2009: 1/5
- 24453599 Imoto 2012: 1/5
- 24612637 Power 2014: 1/5
- 25265472 ADVANCE 2014: 1/5
- 26268221 Lovell 2018: 1/5
- 26647290 Uddin 2016: 1/5
- 26659550 Loebel 2016: 1/5
- 26740092 Lonsdale 2019a: 1/5
- 26955895 Daubenmier 2016: 1/5
- 27018897 Kearing 2016: 1/5
- 27154481 Van Peperstraten 2010: 1/5
- 27242081 Reuland 2017: 1/5

## Optimization Space

1. Accuracy-oriented threshold calibration can likely push the headline metric above 60%, but it should be explicit and separately reported because it relies on dataset label priors for two domains.
2. Real methodological improvement should target `Incomplete outcome data` with structured extraction of randomized/analyzed/missing by arm, dropout reasons, and handling from text/tables/CONSORT flow.
3. `Blinding outcome assessment` needs better outcome-type and assessor-role extraction; the model currently overuses `Unclear` when GT often treats objective outcomes or blinded staff as `Low risk`.
4. The current `article-only` filter removed external evidence but did not require support text phrase alignment; many GT supports are paraphrases or table/figure references, so exact support matching remains noisy.
