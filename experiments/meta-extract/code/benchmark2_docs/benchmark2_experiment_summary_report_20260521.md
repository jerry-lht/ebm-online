# Benchmark2-v2 实验汇报摘要

## 1. 总体任务定义

本实验围绕 benchmark2-v2 的四个正式任务展开，目标是把 study-level 的证据理解、开放世界 item 提出、以及 direct field 抽取串成一条完整链路。

1. Official Item Support：判断官方 item 中的 subgroup 和 timepoint 是否被当前 study 证据支持。
2. Open-world Item Proposal：在不给官方值的条件下主动提出候选 item。
3. Oracle Extraction：在 official item 已知时抽取 direct fields。
4. Routed Extraction：把“先提出 item、再按 item 抽取”串成端到端流程。

## 2. 阶段一：Official Item Support

### 任务定义

这一阶段测的是 closed-world 判别能力。模型需要判断 official item 里的 `subgroup` 和 `timepoint` 是否能被当前 study 文本支持。

### JSON 输入输出示例

```json
{
  "input": {
    "sr_title": "Systematic review title",
    "sr_pico": {"population": "...", "intervention": "...", "comparison": "..."},
    "official_item": {
      "comparison": "A vs B",
      "subgroup": "smokers",
      "timepoints": ["6 months"]
    },
    "evidence_text": "study full text ..."
  },
  "output": {
    "subgroup_support_status": "supported",
    "timepoint_support_status": "not_supported"
  }
}
```


| 项目  | 内容                                                   |
| --- | ---------------------------------------------------- |
| 输入  | SR 标题、SR PICO、official item、study 证据文本               |
| 输出  | `subgroup_support_status`、`timepoint_support_status` |
| 标签  | `supported` / `not_supported` / `uncertain`          |


### 评价方法


| 指标                           | 含义                  |
| ---------------------------- | ------------------- |
| `subgroup_accuracy`          | subgroup 支持判别准确率    |
| `timepoint_accuracy`         | timepoint 支持判别准确率   |
| `subgroup_macro_f1`          | subgroup 三分类宏平均 F1  |
| `timepoint_macro_f1`         | timepoint 三分类宏平均 F1 |
| `subgroup_supported_recall`  | subgroup 正类召回       |
| `timepoint_supported_recall` | timepoint 正类召回      |
| `uncertain_rate`             | 输出 `uncertain` 的比例  |
| `joint_support_consistency`  | 两个字段联合判定的一致性        |


### 实验结果


| 方法                | 数据规模 | subgroup_accuracy | timepoint_accuracy | joint_support_consistency | uncertain_rate | 结论        |
| ----------------- | ---- | ----------------- | ------------------ | ------------------------- | -------------- | --------- |
| full dev baseline | 888  | 0.6577            | 0.6374             | 0.4032                    | 0.1779         | 可用，但一致性一般 |
| split-support v1  | 80   | 0.7125            | 0.8500             | 0.6625                    | 0.0875         | 当前最佳      |


## 3. 阶段二：Open-world Item Proposal

### 任务定义

这一阶段测的是开放世界提出 item 的能力。模型不再拿到官方 `subgroup` / `timepoints`，而是要从 study 文本中主动提出它认为成立的 analysis item。

### JSON 输入输出示例

```json
{
  "input": {
    "sr_title": "Systematic review title",
    "sr_pico": {"population": "...", "intervention": "...", "comparison": "..."},
    "official_parent_context": {
      "outcome_concept": "blood pressure",
      "comparison": "A vs B"
    },
    "evidence_text": "study full text ..."
  },
  "output": {
    "proposed_items": [
      {"subgroup": "smokers", "timepoints": ["6 months"]},
      {"subgroup": null, "timepoints": ["12 months"]}
    ]
  }
}
```


| 项目  | 内容                                                      |
| --- | ------------------------------------------------------- |
| 输入  | SR 标题、SR PICO、`outcome_concept`、`comparison`、study 证据文本 |
| 输出  | `proposed_items`                                        |


### 方法说明

`proposal:negative_examples_ebm` 是当前 proposal 阶段的保留方法。其核心是在 prompt 中加入针对 EBM 场景的负例约束，显式告诉模型哪些内容不应被当作 analysis item（例如 treatment arm、样本描述、泛化 follow-up 描述等），从而抑制过提并提升结构化命中。

### 评价方法


| 指标                                   | 含义             |
| ------------------------------------ | -------------- |
| `subgroup precision / recall / F1`   | subgroup 提出质量  |
| `timepoint precision / recall / F1`  | timepoint 提出质量 |
| `structured precision / recall / F1` | 配对结构质量         |
| `supported_extra_count`              | 支持型多提          |
| `unsupported_extra_count`            | 非支持型多提         |
| `conflicting_extra_count`            | 冲突型多提          |


### 实验结果


| 方法                               | 实验规模    | subgroup F1 | timepoint F1 | structured F1 | conflicting_extra_count | 现象         |
| -------------------------------- | ------- | ----------- | ------------ | ------------- | ----------------------- | ---------- |
| `proposal:negative_examples_ebm` | 80（dev） | 0.5421      | 0.3000       | 0.4580        | 81                      | 当前最佳，边界最清楚 |


## 4. 阶段三：Oracle Extraction

### 任务定义

这一阶段测的是在 official item 已知时，模型能否从 study 文本中抽取出对应的 direct rows。

### 方法简述

当前主方法是 `results_slice_few_shot`：输入侧只保留与抽取最相关的证据切片（`abstract + results sections + tables`），减少无关段落干扰；同时用 few-shot 示例约束输出为规范的 `direct_extraction_fields` 结构，重点提升 row 对齐和字段映射的稳定性。

### JSON 输入输出示例

```json
{
  "input": {
    "official_item": {
      "comparison": "A vs B",
      "subgroup": "smokers",
      "timepoints": ["6 months"]
    },
    "setting_context": {
      "outcome_concept": "blood pressure"
    },
    "evidence_sections": ["abstract", "results", "tables"]
  },
  "output": {
    "predicted_rows": [
      {
        "direct_extraction_fields": [
          {"field": "Experimental N", "value": "52"},
          {"field": "Control N", "value": "50"},
          {"field": "Experimental mean", "value": "4.2"},
          {"field": "Control mean", "value": "6.1"}
        ]
      }
    ]
  }
}
```


| 项目  | 内容                                               |
| --- | ------------------------------------------------ |
| 输入  | official item、setting context、证据切片               |
| 输出  | `predicted_rows`，每行包含 `direct_extraction_fields` |


### 评价方法


| 指标                      | 含义            |
| ----------------------- | ------------- |
| `field F1`              | 字段级抽取质量       |
| `row F1`                | row 级抽取质量     |
| `item exact match`      | 单 item 是否完全匹配 |
| `complete_row_rate`     | 完整 row 命中率    |
| `empty_prediction_rate` | 空预测比例         |
| `per_data_type`         | 按数据类型拆分结果     |
| `per_field`             | 按字段拆分结果       |


### 实验结果


| 方法                          | field F1 | row F1 | item exact match | empty_prediction_rate | 结论            |
| --------------------------- | -------- | ------ | ---------------- | --------------------- | ------------- |
| `results_slice_few_shot` v1 | 0.2740   | 0.1239 | 0.1214           | 0.2060                | baseline 可用   |
| `results_slice_few_shot` v2 | 0.2636   | 0.1382 | 0.1286           | 0.2845                | row 对齐略好，但更保守 |


### 有真实数值出现在输入证据中的子集结果


| 指标                                  | 数值  |
| ----------------------------------- | --- |
| all_gold_numeric_values_present     | 406 |
| partial_gold_numeric_values_present | 382 |
| no_gold_numeric_values_present      | 52  |
| no_gold_numeric_values              | 48  |


说明：以上是 `dev=888` 的 source coverage 审计计数，表示 gold 数值在当前输入证据中的可见性。


| 子集评测口径（基于 full dev 方法）                           | 样本规模 | field F1 | row F1 | item exact match | empty_prediction_rate | 说明                                                       |
| ------------------------------------------------ | ---- | -------- | ------ | ---------------- | --------------------- | -------------------------------------------------------- |
| `results_slice_few_shot` v1 在 all-present 子集上的结果 | 406  | 0.4707   | 0.2228 | 0.2192           | 0.1182                | 从 full dev v1 结果中过滤 `all_gold_numeric_values_present` 得到 |
| `results_slice_few_shot` v2 在 all-present 子集上的结果 | 406  | 0.4500   | 0.2568 | 0.2340           | 0.2414                | 从 full dev v2 结果中过滤 `all_gold_numeric_values_present` 得到 |


