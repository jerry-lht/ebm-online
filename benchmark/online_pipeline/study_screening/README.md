# Study Screening Benchmark

本 benchmark 评估 Study Screening 模块中的 Article Screening 子任务：根据 review question、纳入/排除标准和候选文献内容，判断该文章应 `include` 还是 `exclude`。

当前使用 CSMeD-FT full-text screening fixtures。CSMeD-FT 已提供 review-level eligibility criteria，因此本 benchmark 不评估 screening criteria generation。

## 1. 数据映射

每条 CSMeD-FT example 会映射为一个 workflow-compatible screening 输入：

- `review_title` -> `question_text`
- `criteria_text` -> `screening_criteria.inclusion`
- candidate `title`、`abstract`、`main_text` -> 一个 `CleanedArticle`
- `decision` -> `gold_decision`

构建命令：

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/benchmark.py build \
  --module study_screening \
  --source csmed_ft \
  --dataset-name csmed_ft \
  --seed 42
```

builder 会从 `WojciechKusa/systematic-review-datasets` 下载 `data/CSMeD/CSMeD-FT.zip`，保留官方 `dev` 和 `test` split，并使用 seed `42` 从官方 dev 中采样 5 条 smoke split。

dataset root 保留完整 `instances.jsonl` 和 `gold.jsonl`。context truncation 只在 evaluation runtime 发生。

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
      <td><code>csmed_ft</code></td>
      <td>3333</td>
      <td>5</td>
      <td>644</td>
      <td>636</td>
      <td><a href="datasets/csmed_ft/schema.md">schema.md</a></td>
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
      <td><code>question_text</code>, <code>screening_criteria</code>, <code>articles</code></td>
    </tr>
    <tr>
      <td>Gold</td>
      <td><code>gold_decision</code>, <code>gold_reason</code>, <code>study_id</code></td>
    </tr>
    <tr>
      <td>预测目标</td>
      <td><code>StudyScreeningResult</code> include / exclude decision</td>
    </tr>
    <tr>
      <td>指标</td>
      <td><code>include_precision</code>, <code>include_recall</code>, <code>include_f1</code>, <code>accuracy</code>, <code>false_negative_count</code></td>
    </tr>
  </tbody>
</table>

## 4. 运行示例

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/benchmark.py run \
  --module study_screening \
  --dataset-name csmed_ft \
  --split smoke \
  --method gold \
  --run-id csmed-ft-smoke-gold \
  --limit 5 \
  --section-policy abstract_plus_fulltext \
  --max-full-text-chars 12000
```

`--method gold` 是 benchmark-only baseline，会直接输出 gold screening decision，用于验证 dataset mapping、metrics 和 artifact writing path。

真实 method 需要实现：

```python
run_article_screening(question_text, screening_criteria, articles)
```

运行产物写入：

```text
benchmark/online_pipeline/study_screening/runs/<run_id>/
```

跨 run 对比表：

```text
benchmark/online_pipeline/study_screening/runs/metrics_index.csv
```
