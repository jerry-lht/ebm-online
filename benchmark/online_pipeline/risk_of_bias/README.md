# Risk of Bias Benchmark

本 benchmark 评估 Module 5：固定 RoB 1 七域的 study-level risk-of-bias assessment。

评估单位是一个 included study。method 需要基于 linked cleaned articles 输出该 study 在 RoB 1 domains 上的 judgement。

## 1. 数据来源

dataset 从 SR source materials 重建，不直接复制一个已经 join 好的 benchmark 文件。

raw snapshot 结构：

```text
benchmark/online_pipeline/raw_data/risk_of_bias/
  source_reviews/<CD_NUMBER>/source_review.json
  study_links/<CD_NUMBER>/studies/*.json
  indexes/rob_source_inventory.csv
  indexes/rob_source_manifest.json
```

数据来源说明：

- Gold labels 从 `source_review.json.characteristics_of_studies.included[*].risk_of_bias` 重建。
- Study links 来自上游 `studies/*.json` 文件。
- Characteristics matching 沿用之前的 RoB cleaning 逻辑：先做 normalized `study_id` exact match，再对带有 notes 污染的 source-review IDs 做唯一 suffix match。
- Article content 复用 `benchmark/online_pipeline/raw_data/cleaned_articles` snapshot，正常 build 不重新清洗 XML。
- `instances.jsonl` 不包含 gold 或 article text，只存 `article_ids`。

## 2. 构建

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/benchmark.py build \
  --module risk_of_bias \
  --source cochrane_rob1 \
  --dataset-name cochrane_rob1 \
  --seed 42
```

builder 只保留有 cleaned article content 且关键 benchmark 字段非空的记录：

- `sr_pico.population/intervention/comparison/outcome`
- `characteristics.participants/interventions/outcomes/notes`

Gold 可能只包含 RoB 1 domains 的一个非完整子集。评估时只评估可用 domain，缺失 GT domain 会跳过。当同一个 normalized domain 存在多个 source rows 时，gold label 使用 worst-case merge：

```text
high_risk > unclear_risk > low_risk
```

split 可复现：seed `42` 下 dev/test 为 4:6，smoke 从 dev 中采样 5 条。

当前 `cochrane_rob1` build 包含 348 个 instances 和 341 个 unique articles。它覆盖了历史 RoB 清洗数据中的全部 339 个 PMID records；另外多出 2 个 PMID，是因为同一篇文章被另一个通过当前 source-review quality filter 的 review-level study instance 关联。

## 3. 当前数据分布

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
      <td><code>cochrane_rob1</code></td>
      <td>348</td>
      <td>5</td>
      <td>171</td>
      <td>177</td>
      <td><a href="datasets/cochrane_rob1/schema.md">schema.md</a></td>
    </tr>
  </tbody>
</table>

## 4. 数据契约

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
      <td><code>included_studies</code>, <code>article_ids</code>, <code>study_id</code>, <code>review_id</code></td>
    </tr>
    <tr>
      <td>Gold</td>
      <td><code>risk_of_bias[*].domain</code>, <code>risk_of_bias[*].judgement</code>, <code>support_text</code></td>
    </tr>
    <tr>
      <td>预测目标</td>
      <td>固定 RoB 1 domains 上的 <code>RiskOfBiasAssessment[]</code></td>
    </tr>
    <tr>
      <td>指标</td>
      <td><code>domain_macro_f1</code>, <code>accuracy</code>, <code>high_risk_recall</code>, <code>domain_coverage_rate</code></td>
    </tr>
  </tbody>
</table>

## 5. 评估

RoB evaluation 是 deterministic classification，不使用 LLM judge。

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/risk_of_bias/evaluation/runner.py \
  --dataset benchmark/online_pipeline/risk_of_bias/datasets/cochrane_rob1/splits/smoke \
  --method gold \
  --run-id smoke_gold
```

LLM method smoke：

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/risk_of_bias/evaluation/runner.py \
  --dataset benchmark/online_pipeline/risk_of_bias/datasets/cochrane_rob1/splits/smoke \
  --method risk_of_bias.method_onestep_llm \
  --llm-config llm.local.json \
  --workers 2 \
  --resume \
  --limit 5 \
  --run-id smoke_onestep_llm
```

run outputs 写入 `runs/<run_id>/`：

```text
predictions.jsonl
prediction_failures.jsonl
comparisons.jsonl
metrics.json
summary.json
summary.md
run_manifest.json
metrics_index_row.json
```

跨 run 对比表：

```text
runs/metrics_index.csv
```

主指标：

- `accuracy`
- `macro_f1`
- `high_risk_recall`
- `domain_macro_f1`
- `domain_coverage_rate`

## 6. Method

`risk_of_bias.method_onestep_llm` 实现 workflow port：

```python
run(included_studies: list[str], articles: list[CleanedArticle]) -> list[RiskOfBiasAssessment]
```

method 只消费 article sections 和 tables，不接收 SR characteristics 或 benchmark gold。

前五个 domain 使用从历史 RoB 实验迁移来的 LLM prompts：

- `random_sequence_generation`
- `allocation_concealment`
- `blinding_participants_personnel`
- `blinding_outcome_assessment`
- `incomplete_outcome_data`

`selective_reporting` 和 `other_bias` 当前是 baseline fallback，在 method 内返回 `unclear_risk`。
