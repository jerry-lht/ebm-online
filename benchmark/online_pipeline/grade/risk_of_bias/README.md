# GRADE Domain: Risk of Bias

本 domain 评估 GRADE 四域中的偏倚风险降级判断。评估单位是一个 SoF row 对应的 evidence body。

## 1. 任务边界

method 需要判断该 SoF row 是否因为纳入研究存在方法学偏倚风险而需要降级。

该 domain 不重新阅读全文生成 RoB 1 study-level judgement；它只基于上游 Risk of Bias 模块输出和 domain evidence 判断 GRADE 是否降级。

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
      <td><code>grade_v3</code></td>
      <td>569</td>
      <td>1</td>
      <td>278</td>
      <td>210</td>
      <td><a href="datasets/grade_v3/schema.md">schema.md</a></td>
    </tr>
  </tbody>
</table>

## 3. 输入依据

<table>
  <thead>
    <tr>
      <th>字段</th>
      <th>作用</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>sof_context</code></td>
      <td>当前 SoF row 的 outcome、comparison 和 effect context。</td>
    </tr>
    <tr>
      <td><code>evidence_body</code> / <code>included_study_ids</code></td>
      <td>参与该 SoF row 证据综合的研究集合。</td>
    </tr>
    <tr>
      <td><code>domain_evidence</code></td>
      <td>偏倚风险相关证据，主要来自上游 study-level RoB judgements 的汇总。</td>
    </tr>
    <tr>
      <td><code>effect_estimate</code></td>
      <td>该 evidence body 的效应估计上下文，用于理解偏倚风险对结果可信度的影响。</td>
    </tr>
  </tbody>
</table>

## 4. 输出与指标

Gold 和 prediction 都是一个 GRADE domain judgement：

- `judgement.downgraded`
- `judgement.severity`
- `judgement.levels`
- `judgement.level_evaluable`

主要指标：

- `all_fields_exact_rate`
- `downgraded_exact_rate`
- `severity_exact_rate`
- `levels_exact_rate`
- `evaluable_exact_rate`

## 5. 运行

```bash
PYTHONPATH=backend/src python benchmark/online_pipeline/grade/risk_of_bias/evaluation/runner.py \
  --method method_test \
  --run-id smoke-risk-of-bias
```

结果写入：

```text
benchmark/online_pipeline/grade/risk_of_bias/runs/<run_id>/
```
