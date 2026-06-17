# meta_analysis subtask2 dataset

Files:
- `instances.jsonl`
  - `instance_id`: stable instance key derived from one `AnalysisSetting`
  - `review_id`: Cochrane review ID
  - `analysis_setting`: cleaned setting definition with
    - `setting_id`, `setting_family_id`, `candidate_id`
    - `analysis_group`, `analysis_number`, `analysis_name`, `analysis_group_name`
    - `population_scope`, `comparison`, `comparison_structure`
    - `outcome`, `timepoint`, `subgroup`, `subgroup_scope`
    - `data_type`, `effect_measure`
    - `eligible_study_ids`, `source_context`, `scope_flags`, `setting_quality`
  - `included_studies`: eligible study IDs for this setting instance
  - `article_ids`: article IDs available in `../shared/article_index.jsonl`
  - `article_study_links`: `study_id -> article_id` links for this instance
  - `article_coverage`: coverage summary with eligible count, linked count, missing study IDs,
    linked gold row count, excluded missing-article gold row count, and `coverage_status`
  - `source_context`: auxiliary context such as study-row footnotes
  - `source_refs`: source provenance including official analysis key
- shared article layer
  - `../shared/article_index.jsonl`: `article_id`, `study_id`, `relative_path`, `source`, `table_count`, `has_xml_content`
  - `../shared/articles/*.json`: cleaned article payloads consumed by Subtask 2 methods
- `gold.jsonl`
  - `instance_id`, `review_id`, `source`
  - `study_result_rows`: official joined study rows whose `study_id` has at least one linked article; each row contains
    - `row_id`, `setting_id`, `study_id`, `study_year`, `footnote`
    - `extraction_status`, `data_type`
    - `comparison`, `outcome`, `subgroup`
    - `result_data`
    - `source`
