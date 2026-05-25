# Optimized direct workflow on cleaned core100

## rob_core_dataset first 100

- Studies: 100
- Domains: 500
- Accuracy: 294/500 (58.8%)

| Domain | Correct | Accuracy | GT distribution | Pred distribution |
|---|---:|---:|---|---|
| random sequence generation | 80/100 | 80.0% | Low risk:67, Unclear risk:30, High risk:3 | Low risk:59, Unclear risk:40, High risk:1 |
| allocation concealment | 69/100 | 69.0% | Unclear risk:50, Low risk:43, High risk:7 | Unclear risk:55, Low risk:44, High risk:1 |
| blinding of participants and personnel | 57/100 | 57.0% | High risk:38, Unclear risk:35, Low risk:27 | Low risk:36, High risk:36, Unclear risk:28 |
| blinding of outcome assessment | 48/100 | 48.0% | Low risk:45, High risk:29, Unclear risk:26 | Unclear risk:49, Low risk:35, High risk:16 |
| incomplete outcome data | 40/100 | 40.0% | Low risk:53, Unclear risk:25, High risk:22 | Unclear risk:47, Low risk:46, High risk:7 |

Top error types:

- gt_support_not_found_in_article_text: 119
- over-inferred_from_sparse_reporting: 34
- under-called_due_to_missing_or_underused_evidence: 31
- external_or_review_context_needed: 8
- figure_table_or_supplement_needed: 7
- blinding_outcome_type_or_role_confusion: 6
- allocation_concealment_detail_threshold: 1

## subset also in rob_article_only_dataset

- Studies: 81
- Domains: 405
- Accuracy: 247/405 (61.0%)

| Domain | Correct | Accuracy | GT distribution | Pred distribution |
|---|---:|---:|---|---|
| random sequence generation | 65/81 | 80.2% | Low risk:53, Unclear risk:26, High risk:2 | Low risk:46, Unclear risk:34, High risk:1 |
| allocation concealment | 56/81 | 69.1% | Unclear risk:41, Low risk:34, High risk:6 | Unclear risk:44, Low risk:36, High risk:1 |
| blinding of participants and personnel | 50/81 | 61.7% | High risk:35, Unclear risk:25, Low risk:21 | High risk:29, Low risk:28, Unclear risk:24 |
| blinding of outcome assessment | 39/81 | 48.1% | Low risk:36, High risk:25, Unclear risk:20 | Unclear risk:38, Low risk:32, High risk:11 |
| incomplete outcome data | 37/81 | 45.7% | Low risk:46, Unclear risk:18, High risk:17 | Unclear risk:42, Low risk:35, High risk:4 |

Top error types:

- gt_support_not_found_in_article_text: 94
- under-called_due_to_missing_or_underused_evidence: 26
- over-inferred_from_sparse_reporting: 26
- figure_table_or_supplement_needed: 6
- blinding_outcome_type_or_role_confusion: 5
- allocation_concealment_detail_threshold: 1

## core100 not in article-only

- Studies: 19
- Domains: 95
- Accuracy: 47/95 (49.5%)

| Domain | Correct | Accuracy | GT distribution | Pred distribution |
|---|---:|---:|---|---|
| random sequence generation | 15/19 | 78.9% | Low risk:14, Unclear risk:4, High risk:1 | Low risk:13, Unclear risk:6 |
| allocation concealment | 13/19 | 68.4% | Unclear risk:9, Low risk:9, High risk:1 | Unclear risk:11, Low risk:8 |
| blinding of participants and personnel | 7/19 | 36.8% | Unclear risk:10, Low risk:6, High risk:3 | Low risk:8, High risk:7, Unclear risk:4 |
| blinding of outcome assessment | 9/19 | 47.4% | Low risk:9, Unclear risk:6, High risk:4 | Unclear risk:11, High risk:5, Low risk:3 |
| incomplete outcome data | 3/19 | 15.8% | Low risk:7, Unclear risk:7, High risk:5 | Low risk:11, Unclear risk:5, High risk:3 |

Top error types:

- gt_support_not_found_in_article_text: 25
- over-inferred_from_sparse_reporting: 8
- external_or_review_context_needed: 8
- under-called_due_to_missing_or_underused_evidence: 5
- blinding_outcome_type_or_role_confusion: 1
- figure_table_or_supplement_needed: 1

## first 20

- Studies: 20
- Domains: 100
- Accuracy: 62/100 (62.0%)

| Domain | Correct | Accuracy | GT distribution | Pred distribution |
|---|---:|---:|---|---|
| random sequence generation | 17/20 | 85.0% | Low risk:14, Unclear risk:6 | Low risk:13, Unclear risk:7 |
| allocation concealment | 12/20 | 60.0% | Unclear risk:10, Low risk:9, High risk:1 | Unclear risk:13, Low risk:7 |
| blinding of participants and personnel | 12/20 | 60.0% | Unclear risk:8, High risk:8, Low risk:4 | Low risk:9, Unclear risk:6, High risk:5 |
| blinding of outcome assessment | 12/20 | 60.0% | Low risk:11, Unclear risk:5, High risk:4 | Unclear risk:9, Low risk:8, High risk:3 |
| incomplete outcome data | 9/20 | 45.0% | Low risk:13, Unclear risk:5, High risk:2 | Low risk:10, Unclear risk:8, High risk:2 |

Top error types:

- gt_support_not_found_in_article_text: 21
- over-inferred_from_sparse_reporting: 7
- figure_table_or_supplement_needed: 3
- under-called_due_to_missing_or_underused_evidence: 3
- blinding_outcome_type_or_role_confusion: 2
- external_or_review_context_needed: 1
- allocation_concealment_detail_threshold: 1

## remaining 80

- Studies: 80
- Domains: 400
- Accuracy: 232/400 (58.0%)

| Domain | Correct | Accuracy | GT distribution | Pred distribution |
|---|---:|---:|---|---|
| random sequence generation | 63/80 | 78.8% | Low risk:53, Unclear risk:24, High risk:3 | Low risk:46, Unclear risk:33, High risk:1 |
| allocation concealment | 57/80 | 71.2% | Unclear risk:40, Low risk:34, High risk:6 | Unclear risk:42, Low risk:37, High risk:1 |
| blinding of participants and personnel | 45/80 | 56.2% | High risk:30, Unclear risk:27, Low risk:23 | High risk:31, Low risk:27, Unclear risk:22 |
| blinding of outcome assessment | 36/80 | 45.0% | Low risk:34, High risk:25, Unclear risk:21 | Unclear risk:40, Low risk:27, High risk:13 |
| incomplete outcome data | 31/80 | 38.8% | Low risk:40, Unclear risk:20, High risk:20 | Unclear risk:39, Low risk:36, High risk:5 |

Top error types:

- gt_support_not_found_in_article_text: 98
- under-called_due_to_missing_or_underused_evidence: 28
- over-inferred_from_sparse_reporting: 27
- external_or_review_context_needed: 7
- blinding_outcome_type_or_role_confusion: 4
- figure_table_or_supplement_needed: 4

## Target Domain Details: core100

### blinding of outcome assessment

- Accuracy: 48/100 (48.0%)

Confusions:

- Low risk -> Unclear risk: 19
- High risk -> Unclear risk: 13
- High risk -> Low risk: 8
- Unclear risk -> High risk: 5
- Unclear risk -> Low risk: 4
- Low risk -> High risk: 3

### incomplete outcome data

- Accuracy: 40/100 (40.0%)

Confusions:

- Low risk -> Unclear risk: 22
- High risk -> Unclear risk: 14
- Unclear risk -> Low risk: 11
- High risk -> Low risk: 7
- Low risk -> High risk: 3
- Unclear risk -> High risk: 3

## Target Domain Details: article-only subset

### blinding of outcome assessment

- Accuracy: 39/81 (48.1%)

Confusions:

- Low risk -> Unclear risk: 14
- High risk -> Unclear risk: 11
- High risk -> Low risk: 8
- Unclear risk -> Low risk: 4
- Unclear risk -> High risk: 3
- Low risk -> High risk: 2

### incomplete outcome data

- Accuracy: 37/81 (45.7%)

Confusions:

- Low risk -> Unclear risk: 19
- High risk -> Unclear risk: 12
- Unclear risk -> Low risk: 6
- High risk -> Low risk: 4
- Low risk -> High risk: 2
- Unclear risk -> High risk: 1
