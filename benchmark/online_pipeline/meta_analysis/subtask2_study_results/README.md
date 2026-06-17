# Meta Analysis Subtask 2: Study Result Rows

本 subtask 评估 study-level result data extraction。评估单位是一个 `AnalysisSetting` 对应的 extraction instance。

## 1. 任务边界

method 需要根据 `analysis_setting`、eligible studies、linked cleaned articles 和 source context，抽取该 setting 下可用于 meta-analysis 的 `study_result_rows`。

该 subtask 不负责选择 analysis model，不负责计算 subgroup 或 overall pooled estimates。

## 2. 当前数据分布

<table>
  <thead>
    <tr>
      <th>Dataset</th>
      <th>All</th>
      <th>Smoke</th>
      <th>Dev</th>
      <th>Test</th>
      <th>Schema</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>cochrane_meta_v1</code></td>
      <td>2504</td>
      <td>5</td>
      <td>1246</td>
      <td>1258</td>
      <td><a href="datasets/cochrane_meta_v1/schema.md">schema.md</a></td>
    </tr>
  </tbody>
</table>

## 3. 数据契约

<table>
  <thead>
    <tr>
      <th>Item</th>
      <th>Fields</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>输入</td>
      <td><code>analysis_setting</code>, <code>included_studies</code>, <code>article_ids</code>, <code>article_study_links</code>, <code>article_coverage</code>, <code>source_context</code>, <code>source_refs</code></td>
    </tr>
    <tr>
      <td>共享文章层</td>
      <td><code>shared/article_index.jsonl</code>, <code>shared/articles/*.json</code></td>
    </tr>
    <tr>
      <td>Gold 输出</td>
      <td><code>study_result_rows</code></td>
    </tr>
    <tr>
      <td>预测目标</td>
      <td>与 gold 可 join 的 study-level result rows，包括 study、data type、comparison/outcome/subgroup 和 result data。</td>
    </tr>
    <tr>
      <td>主要指标</td>
      <td><code>subtask2_exact_row_rate</code>, <code>subtask2_numeric_close_rate</code>, <code>field_completion_rate</code></td>
    </tr>
  </tbody>
</table>

## 4. 运行

```bash
PYTHONPATH=backend/src python benchmark/online_pipeline/meta_analysis/subtask2_study_results/evaluation/runner.py \
  --method method_test \
  --run-id smoke-subtask2
```

结果写入：

```text
benchmark/online_pipeline/meta_analysis/subtask2_study_results/runs/<run_id>/
```
