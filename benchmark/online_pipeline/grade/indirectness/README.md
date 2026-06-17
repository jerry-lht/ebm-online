# GRADE Domain: Indirectness

本 domain 评估 GRADE 四域中的间接性降级判断。评估单位是一个 SoF row 对应的 evidence body。

## 1. 任务边界

method 需要判断纳入证据是否在 population、intervention/comparator、outcome 或适用场景上偏离目标临床问题。

该 domain 不重新做文献筛选，也不重新抽取 study PIO；它只基于上游 question PICO、screening criteria、study-level PIO 和 analysis setting 判断间接性。

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
      <td>709</td>
      <td>3</td>
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
      <td><code>question_text</code> / <code>question_pico</code></td>
      <td>目标临床问题和 question-level PICO。</td>
    </tr>
    <tr>
      <td><code>screening_criteria</code></td>
      <td>纳入/排除标准，用于判断证据适用性。</td>
    </tr>
    <tr>
      <td><code>analysis_setting</code></td>
      <td>当前 SoF row 对齐到的 comparison、outcome、timepoint 和 setting context。</td>
    </tr>
    <tr>
      <td><code>domain_evidence</code></td>
      <td>间接性相关证据，例如 study-level PIO 与目标 PICO 的差异。</td>
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
PYTHONPATH=backend/src python benchmark/online_pipeline/grade/indirectness/evaluation/runner.py \
  --method method_test \
  --run-id smoke-indirectness
```

结果写入：

```text
benchmark/online_pipeline/grade/indirectness/runs/<run_id>/
```
