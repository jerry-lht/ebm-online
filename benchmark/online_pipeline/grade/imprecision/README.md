# GRADE Domain: Imprecision

本 domain 评估 GRADE 四域中的不精确性降级判断。评估单位是一个 SoF row 对应的 evidence body。

## 1. 任务边界

method 需要判断效应估计是否因为置信区间过宽、样本量或事件数不足、跨越重要临床阈值等原因而需要降级。

该 domain 不重新计算 pooled estimate；它只基于上游 Meta Analysis 结果和 imprecision evidence 判断精确性。

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
      <td>707</td>
      <td>1</td>
      <td>276</td>
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
      <td><code>effect_estimate</code></td>
      <td>效应估计、置信区间和 effect measure。</td>
    </tr>
    <tr>
      <td><code>study_result_rows</code></td>
      <td>样本量、事件数或连续变量结果等 study-level result context。</td>
    </tr>
    <tr>
      <td><code>sof_context</code></td>
      <td>SoF row 的 absolute/relative effect context 和 outcome context。</td>
    </tr>
    <tr>
      <td><code>domain_evidence</code></td>
      <td>不精确性相关证据，例如 CI 宽度、事件数、样本量或是否跨越重要阈值。</td>
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
PYTHONPATH=backend/src python benchmark/online_pipeline/grade/imprecision/evaluation/runner.py \
  --method method_test \
  --run-id smoke-imprecision
```

结果写入：

```text
benchmark/online_pipeline/grade/imprecision/runs/<run_id>/
```
