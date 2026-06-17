# Meta Analysis Benchmark

本 benchmark 对齐 `docs/workflow_v3.md` 中的 Module 6：Meta Analysis。

当前不物化 package-level meta-analysis benchmark output，而是把 Module 6 拆成四个独立 subtask benchmark unit：

- `subtask2_study_results`：基于文章的 study-level result data extraction
- `subtask3_analysis_methods`：analysis method / model decision
- `subtask4_subgroup_analysis`：subgroup estimates 和 subgroup-difference tests
- `subtask5_overall_estimates`：overall pooled estimates

模块级 builder 仍从同一套冻结 raw/intermediate data 构建四个 subtasks，确保它们的 source material 一致。

## 1. 数据来源

v1 source 冻结在：

```text
benchmark/online_pipeline/raw_data/meta_analysis/
```

核心文件：

- `source/official_analysis_csv_snapshot/`：官方 Cochrane analysis CSV snapshot
- `intermediate/analysis_family_sources.jsonl`：每个 `review_id + Analysis group + Analysis number` 对应一个 source bundle
- `intermediate/analysis_settings.jsonl`：workflow-shaped analysis settings
- `intermediate/study_result_rows.jsonl`：官方 join 后的 study result rows
- `intermediate/analysis_methods.jsonl`：官方 method/model rows
- `intermediate/overall_estimates.jsonl`：官方 overall pooled estimates
- `intermediate/subgroup_results.jsonl`：官方 subgroup estimates 和 subgroup-difference tests

LLM setting cleaning 只负责结构化 comparison、outcome 和 timepoint。Gold numeric result data、method fields、overall estimates、subgroup estimates 和 subgroup-difference tests 都来自官方 CSV。

## 2. Dataset 结构

每个 subtask 拥有自己的 `datasets`、`evaluation` 和 `runs`：

```text
benchmark/online_pipeline/meta_analysis/subtask2_study_results/
  datasets/cochrane_meta_v1/
  evaluation/runner.py
  runs/

benchmark/online_pipeline/meta_analysis/subtask3_analysis_methods/
  datasets/cochrane_meta_v1/
  evaluation/runner.py
  runs/

benchmark/online_pipeline/meta_analysis/subtask4_subgroup_analysis/
  datasets/cochrane_meta_v1/
  evaluation/runner.py
  runs/

benchmark/online_pipeline/meta_analysis/subtask5_overall_estimates/
  datasets/cochrane_meta_v1/
  evaluation/runner.py
  runs/
```

Subtask 2 带有自己的 article layer：

```text
subtask2_study_results/datasets/cochrane_meta_v1/shared/article_index.jsonl
subtask2_study_results/datasets/cochrane_meta_v1/shared/articles/*.json
```

当前不生成 module-level `meta_analysis/datasets/<dataset_name>/`。builder 只写入可运行的 subtask datasets，并返回 `dataset_dirs` 映射。

## 3. 子任务文档

每个 subtask 的数据契约、指标和运行示例由各自目录维护。

<table>
  <thead>
    <tr>
      <th>Subtask</th>
      <th>任务</th>
      <th>All</th>
      <th>Smoke</th>
      <th>Dev</th>
      <th>Test</th>
      <th>Gold 输出</th>
      <th>Schema</th>
      <th>文档</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>subtask2_study_results</code></td>
      <td>study-level result data extraction</td>
      <td>2504</td>
      <td>5</td>
      <td>1246</td>
      <td>1258</td>
      <td><code>study_result_rows</code></td>
      <td><a href="subtask2_study_results/datasets/cochrane_meta_v1/schema.md">schema.md</a></td>
      <td><a href="subtask2_study_results/README.md">README.md</a></td>
    </tr>
    <tr>
      <td><code>subtask3_analysis_methods</code></td>
      <td>analysis method / model decision</td>
      <td>15122</td>
      <td>5</td>
      <td>5083</td>
      <td>10039</td>
      <td><code>analysis_methods</code></td>
      <td><a href="subtask3_analysis_methods/datasets/cochrane_meta_v1/schema.md">schema.md</a></td>
      <td><a href="subtask3_analysis_methods/README.md">README.md</a></td>
    </tr>
    <tr>
      <td><code>subtask4_subgroup_analysis</code></td>
      <td>subgroup estimates 和 subgroup-difference tests</td>
      <td>8096</td>
      <td>11</td>
      <td>2803</td>
      <td>5293</td>
      <td><code>subgroup_results</code></td>
      <td><a href="subtask4_subgroup_analysis/datasets/cochrane_meta_v1/schema.md">schema.md</a></td>
      <td><a href="subtask4_subgroup_analysis/README.md">README.md</a></td>
    </tr>
    <tr>
      <td><code>subtask5_overall_estimates</code></td>
      <td>overall pooled estimates</td>
      <td>3818</td>
      <td>5</td>
      <td>1345</td>
      <td>2473</td>
      <td><code>overall_estimates</code></td>
      <td><a href="subtask5_overall_estimates/datasets/cochrane_meta_v1/schema.md">schema.md</a></td>
      <td><a href="subtask5_overall_estimates/README.md">README.md</a></td>
    </tr>
  </tbody>
</table>

## 4. 构建

```bash
PYTHONPATH=backend/src python benchmark/online_pipeline/meta_analysis/raw_builder.py build-dataset \
  --dataset-name cochrane_meta_v1 \
  --shared-settings-root benchmark/online_pipeline/raw_data/analysis_settings/grade_required_v1
```

## 5. 评估

评估命令由各 subtask README 维护。结果写入各 subtask 的 `runs/` 目录。

## 6. 历史目录策略

旧版 root-level `datasets/`、`evaluation/` 和 `runs/` 目录已归档到：

```text
benchmark/online_pipeline/archive/20260617_subtask_domain_layout/meta_analysis/
```
