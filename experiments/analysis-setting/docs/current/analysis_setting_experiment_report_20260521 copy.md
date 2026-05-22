# Analysis Setting 实验汇报（2026-05-21）

## 1. 背景与目标

传统 meta-analysis 里，真正被汇总的单位一条 pooled analysis。它通常会带有：

当前是先恢复这条 pooled analysis 背后的 `analysis setting`。

给定一个系统综述和一个 gold `outcome_concept`，模型能不能判断这个 outcome 在综述里是按什么统计类型、什么 effect measure、什么 comparison 结构来做 meta-analysis 的。

当前任务单位是：

- `data_type`: `(review, outcome_concept)`
- `candidate_effect_measure`: `(review, outcome_concept, data_type)`
- `comparisons`: `(review, outcome_concept)`

一个直观示例如下：

```json
{
  "review_id": "CD014874",
  "sr_title": "Psychological and educational interventions for preventing postpartum depression",
  "input": {
    "sr_pico": "postnatal women; psychological interventions; inactive control",
    "outcome_concept": "postpartum depression symptom severity at postintervention",
    "evidence_mode": "full-text"
  },
  "target": {
    "data_type": "continuous",
    "candidate_effect_measure": "std mean difference",
    "comparisons": [
      "psychological interventions vs inactive control"
    ]
  }
}
```

## 2. 实验设定

- 输入：`SR title`、`SR PICO`、included studies evidence
- 条件锚点：gold `outcome_concept`
- 模型：`gpt-5.4-mini`
- 证据模式：`abstract-only` 或 `full-text`
- 评测方式：条件化字段级评测，不混入 outcome 生成错误

## 3. 阶段一：Data Type

任务：给定 gold `outcome_concept`，预测该 outcome 的统计类型，即 `continuous`、`dichotomous` 或 `contrast level`。

总体指标：


| 指标               | 数值       |
| ---------------- | -------- |
| `instance_count` | `388`    |
| `accuracy`       | `0.9046` |
| `macro_f1`       | `0.6078` |


分标签结果：


| 标签               | support | precision | recall   | f1       |
| ---------------- | ------- | --------- | -------- | -------- |
| `continuous`     | `184`   | `0.9527`  | `0.8750` | `0.9122` |
| `dichotomous`    | `198`   | `0.8676`  | `0.9596` | `0.9113` |
| `contrast level` | `6`     | `0.0000`  | `0.0000` | `0.0000` |


## 4. 阶段二：Candidate Effect Measure

任务：给定 gold `outcome_concept` 和 gold `data_type`，预测该 outcome 对应的 `candidate_effect_measure`。

本文只保留一个主方法：

- 方法：`standard_fulltext_evidence + free_generation`
- 含义：直接使用 `full-text` 证据，让模型在给定 gold `data_type` 的前提下自由生成 effect measure

总体指标：


| 指标               | 数值       |
| ---------------- | -------- |
| `instance_count` | `1098`   |
| `accuracy`       | `0.7213` |
| `macro_f1`       | `0.4216` |


按 `data_type` 的准确率：


| data_type        | accuracy |
| ---------------- | -------- |
| `continuous`     | `0.5946` |
| `contrast level` | `0.6111` |
| `dichotomous`    | `0.8316` |


## 5. 阶段三：Comparisons

任务：给定 gold `outcome_concept`，恢复 benchmark 中定义的 review-level `comparisons` labels。

这里的重点是：模型输出的不是单篇研究里的 intervention-comparator pair，而是综述层面真正用来组织 meta-analysis 结果的 comparison label。

例子：

```json
{
  "review_id": "CD014874",
  "outcome_concept": "psychological wellbeing at postintervention",
  "prediction_target": {
    "comparisons": [
      "psychological interventions vs inactive control"
    ]
  }
}
```

这里的 gold label 可能是一个 review-level grouped label，而不是更细的 study-level pair，如 `CBT vs waitlist` 或 `IPT vs usual care`。

本文只保留一个当前最好的方法：

- 方法：`constrained-selection v2`
- 含义：先构造 comparison candidates，再让模型在候选集中做 selection，目标是减少自由生成带来的 label drift 和过度展开

`dev20` 结果来自：`（test 过拟合）`


| 指标                                  | 数值       |
| ----------------------------------- | -------- |
| `comparison_only.normalized_set_f1` | `0.2766` |
| `exact_set_match_rate`              | `0.1579` |
| `comparison_count_accuracy`         | `0.3158` |
| `missing`                           | `69`     |
| `extra`                             | `58`     |
| `grouped_vs_atomic`                 | `0`      |
| `broad_vs_narrow`                   | `11`     |


同一方法在 `test200` 上的结果：


| 指标                                  | 数值       |
| ----------------------------------- | -------- |
| `comparison_only.normalized_set_f1` | `0.0211` |
| `exact_set_match_rate`              | `0.0211` |
| `comparison_count_accuracy`         | `0.3526` |
| `missing`                           | `325`    |
| `extra`                             | `779`    |
| `grouped_vs_atomic`                 | `113`    |
| `broad_vs_narrow`                   | `31`     |


补充的 hallucination 指标：


| 子集        | `hallucinated_comparison_rate` | `mean_predicted_count` |
| --------- | ------------------------------ | ---------------------- |
| `dev20`   | `1.0`                          | `1.0`                  |
| `test200` | `1.0`                          | `3.3`                  |


一句话结论：`comparisons` 目前仍然明显难于前两个阶段。