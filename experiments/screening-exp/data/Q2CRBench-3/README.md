---
language:
- en
license: apache-2.0
dataset_info:
- config_name: Clinical_Questions
  features:
  - name: Aspect
    dtype: string
  - name: Index
    dtype: string
  - name: Question
    dtype: string
  - name: P
    dtype: string
  - name: I
    dtype: string
  - name: C
    sequence: string
  - name: O
    dtype: string
  - name: S
    dtype: string
  - name: Dataset
    dtype: string
  splits:
  - name: train
    num_bytes: 84370
    num_examples: 99
  download_size: 30092
  dataset_size: 84370
- config_name: Evidence_Profiles-Outcome
  features:
  - name: outcome_uid
    dtype: string
  - name: clinical_question
    dtype: string
  - name: population
    dtype: string
  - name: intervention
    dtype: string
  - name: comparator
    dtype: string
  - name: outcome
    dtype: string
  - name: importance
    dtype: string
  - name: related_paper_list
    sequence: string
  - name: assessment_results
    dtype: string
  - name: PICO_IDX
    dtype: string
  - name: Database
    dtype: string
  splits:
  - name: train
    num_bytes: 798252
    num_examples: 563
  download_size: 108223
  dataset_size: 798252
- config_name: Evidence_Profiles-Paper
  features:
  - name: title
    dtype: string
  - name: paper_uid
    dtype: string
  - name: reference
    dtype: string
  - name: study_design
    dtype: string
  - name: characteristics
    dtype: string
  - name: PICO_IDX
    dtype: string
  - name: Database
    dtype: string
  - name: pmid
    dtype: string
  splits:
  - name: train
    num_bytes: 153067
    num_examples: 262
  download_size: 62757
  dataset_size: 153067
- config_name: Screened_Records
  features:
  - name: Paper_Index
    dtype: int64
  - name: Title
    dtype: string
  - name: Published
    dtype: string
  - name: Abstract
    dtype: string
  - name: Digital Object Identifier
    dtype: string
  - name: Full-text_Assessment
    dtype: string
  - name: Record_Screening
    dtype: 'null'
  - name: Reason_for_Exclusion_at_Full-text
    dtype: 'null'
  - name: Dataset
    dtype: string
  - name: Search_Strategy_ID
    dtype: int64
  - name: PICO_IDX
    dtype: string
  splits:
  - name: train
    num_bytes: 31182470
    num_examples: 16321
  download_size: 15552275
  dataset_size: 31182470
- config_name: Search_Strategies
  features:
  - name: Search_Strategy_ID
    dtype: int64
  - name: Search_Strategy
    dtype: string
  - name: Platform
    dtype: string
  - name: Search_for_PICO_IDX
    sequence: string
  - name: Dataset
    dtype: string
  splits:
  - name: train
    num_bytes: 29217
    num_examples: 19
  download_size: 22383
  dataset_size: 29217
configs:
- config_name: Clinical_Questions
  data_files:
  - split: train
    path: Clinical_Questions/train-*
- config_name: Evidence_Profiles-Outcome
  data_files:
  - split: train
    path: Evidence_Profiles-Outcome/train-*
- config_name: Evidence_Profiles-Paper
  data_files:
  - split: train
    path: Evidence_Profiles-Paper/train-*
- config_name: Screened_Records
  data_files:
  - split: train
    path: Screened_Records/train-*
- config_name: Search_Strategies
  data_files:
  - split: train
    path: Search_Strategies/train-*
tags:
- medical
---
# Q2CRBench-3

`Q2CRBench-3` is a benchmark dataset designed to evaluate the performance of LLM in generating clinical recommendations. It is derived from the development records of three authoritative clinical guidelines: [the 2020 EAN guideline for dementia](https://onlinelibrary.wiley.com/doi/10.1111/ene.14412), [the 2021 ACR guideline for rheumatoid arthritis](https://acrjournals.onlinelibrary.wiley.com/doi/10.1002/art.41752), and [the 2024 KDIGO guideline for chronic kidney disease](https://www.kidney-international.org/article/S0085-2538(23)00766-4/fulltext).

Due to copyright restrictions, we are unable to provide the screened records from the 2020 EAN Dementia and 2021 ACR RA datasets directly. However, you can reproduce them by applying the corresponding search strategies or sending request to us (see [here](https://github.com/somewordstoolate/Quicker/blob/main/Q2CRBench-3/2020%20EAN%20Dementia/desc.md) for more details). We separate evidence profiles into Outcome and Paper two parts, you can assess its raw data version in [Quicker Repository](https://github.com/somewordstoolate/Quicker) if necessary.

More details can be find:

- **Repository:** [Quicker Repository](https://github.com/somewordstoolate/Quicker)
- **Published Article:** [Streamlining Evidence Based Clinical Recommendations with Large Language Models](https://www.nature.com/articles/s41746-025-02273-y) 


