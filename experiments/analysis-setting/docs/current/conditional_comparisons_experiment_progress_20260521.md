# Comparisons 条件实验进度同步（2026-05-21）

## 1. 当前目标

本轮工作围绕 `comparisons` 条件任务展开，重点是把 benchmark 中的 review-level comparison label 恢复得更准确。

当前默认运行前提：

- 模型：`gpt-5.4-mini`
- evidence mode：`full-text`
- 并发：`16`

本轮实际做了三条线：

1. 先清理 `comparisons` evaluator，使主指标不再被 `gold_empty` 污染。
2. 尝试 `constrained_selection` 路线，验证候选筛选是否能降低自由生成误差。
3. 回到 benchmark 定义本身，重写一个 benchmark-aligned free-generation prompt，检查仅靠 prompt 是否足够。

## 2. 已完成的实现

### 2.1 evaluator / normalization 重构

已完成：

- `gold_nonempty` / `gold_empty` 分层统计
- 主结果切到 `comparison_only`
- `gold_empty` 单独输出：
  - `pred_empty_rate`
  - `hallucinated_comparison_rate`
  - `mean_predicted_count`
- comparison-specific conservative normalization：
  - `vs / versus / compared with / compared to`
  - `placebo / placebo control`
  - `usual care / standard care / routine care`

当前主指标解释口径：

- `comparison_only.normalized_set_f1`
- `comparison_only.exact_set_match_rate`
- `comparison_only.comparison_count_accuracy`

### 2.2 prompt / few-shot 分支

已完成：

- `conditional_task_aware_v6_comparisons_review_level`
  - 强调 review-level grouped label
  - 压制 study-level atomic over-generation
- `comparisons_boundary_v1` few-shot
  - 覆盖 grouped vs atomic
  - broad vs narrow
  - `gold_empty`

对应结果目录别名：

- `comparisons_prompt_review_level_v1`
- `comparisons_prompt_review_level_v1__fewshot_comparisons_boundary_v1`

### 2.3 constrained-selection 原型分支

已完成：

- `decision_strategy = constrained_selection`
- `conditional_task_aware_v7_comparisons_selection`
- comparison candidate builder：
  - `conditional_comparison_candidates.py`
- `comparisons_constrained_selection_v1` 结果目录别名

这一分支的目标是：

- 降低自由生成 label drift
- 降低 `extra` / 过度展开
- 通过候选集约束输出空间

### 2.4 benchmark-aligned free-generation prompt 分支

已完成：

- `conditional_task_aware_v8_comparisons_benchmark_aligned`
- `comparisons_prompt_benchmark_aligned_v1` 结果目录别名

这个 prompt 分支明确对齐 benchmark 里的 comparison label 形态：

- comparison 不一定是 `X vs Y`
- 允许 simple label：如 `choice`、`confidence`
- 允许 family label：如 `psychological interventions vs inactive control`
- 允许 atomic + timepoint/subgroup/detail label：如 retainers / `nHFV` 系列 labels

### 2.5 测试

本轮新增或扩展了：

- evaluator tests
- prompting tests
- runner/CLI tests
- comparison candidate builder tests

当前相关 targeted pytest 已通过：

- `21 passed`

## 3. benchmark 定义层面的新认识

本轮重新检查 benchmark 后，`comparisons` 的 gold label 不是单一风格，而是至少包含四类：

1. simple review-level labels
   - `choice`
   - `confidence`
   - `consultation length`
   - `decisional conflict`
2. grouped family labels
   - `psychological interventions vs inactive control`
   - `service system approaches vs inactive control`
   - `mbis versus active comparators`
   - `nhfv vs other non-invasive respiratory therapy modalities`
3. atomic pairwise labels
   - `breast cancer mastectomy vs lumpectomy`
4. atomic labels with detail modifiers
   - retainers timepoint labels
   - `nHFV` subgroup / setting / parameter labels

这意味着：

- 不能把 `comparisons` 简化成“intervention vs comparator pair 抽取”
- 也不能只靠 review-level grouping 规则
- benchmark 要求的是恢复 review 实际使用的 comparison ontology

## 4. 已完成实验

### 4.1 dev20：baseline / prompt / few-shot 对照

固定子集：

- `results/comparisons_dev20_20260521/conditional_splits/full-text/dev_comparisons_dev20.jsonl`

实际对照分支：

- `baseline`
- `prompt_fix`
- `fewshot_fix`

结果：

| 分支 | `comparison_only` F1 | exact match | count acc | hallucination | grouped_vs_atomic | broad_vs_narrow | missing | extra |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline` | `0.1667` | `0.1667` | `0.3889` | `1.0` | `4` | `2` | `75` | `121` |
| `prompt_fix` | `0.1579` | `0.1579` | `0.5263` | `1.0` | `4` | `11` | `85` | `108` |
| `fewshot_fix` | `0.1667` | `0.1667` | `0.4444` | `1.0` | `4` | `5` | `80` | `91` |

结论：

- `prompt_fix` 没提升主恢复指标
- `fewshot_fix` 把 `extra` 从 `121` 压到 `91`
- 但 `fewshot_fix` 没把主 `comparison_only` F1 拉起来

### 4.2 constrained-selection v1：失败原型

固定子集：

- 同一 `dev20`

结果：

- `comparison_only.normalized_set_f1 = 0.0`
- `missing = 88`
- `extra = 63`

结论：

- `extra` 压下来了
- 但候选表质量太差，`oracle coverage` 也是 `0/19`
- 这版结果不能用来支持 constrained-selection

### 4.3 constrained-selection v2：dev20 局部成功

对 candidate builder 做了 `v2` 后：

- `oracle coverage` 提到：
  - `19/19` 至少部分覆盖
  - `13/19` 完整覆盖 gold set

真实 `dev20` 结果：

- `comparison_only.normalized_set_f1 = 0.2766`
- `exact_set_match_rate = 0.1579`
- `missing = 69`
- `extra = 58`
- `grouped_vs_atomic = 0`
- `broad_vs_narrow = 11`

结论：

- 这是 `dev20` 上目前最高的主 F1
- `extra` 也降到了最低
- 但 broad/narrow 误差明显上升

### 4.4 constrained-selection v2：test200 泛化失败

固定子集：

- `results/comparisons_test200_20260521/conditional_splits/full-text/test_comparisons_test200.jsonl`

结果：

- `comparison_only.normalized_set_f1 = 0.0211`
- `exact_set_match_rate = 0.0211`
- `comparison_count_accuracy = 0.3526`
- `missing = 325`
- `extra = 779`
- `grouped_vs_atomic = 113`
- `broad_vs_narrow = 31`

结论：

- `dev20` 上的收益没有泛化到 `test200`
- 当前 constrained-selection v2 明显存在过拟合 dev20 风险
- 不能直接扩到 full test

### 4.5 benchmark-aligned free-generation prompt：dev80 / test200

固定子集：

- `results/comparisons_prompt_benchmark_20260521/conditional_splits/full-text/dev_comparisons_dev80.jsonl`
- `results/comparisons_prompt_benchmark_20260521/conditional_splits/full-text/test_comparisons_test200.jsonl`

结果：

| 子集 | `comparison_only` F1 | exact match | count acc | missing | extra | grouped_vs_atomic | broad_vs_narrow |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `dev80` | `0.0897` | `0.0897` | `0.6795` | `173` | `233` | `40` | `22` |
| `test200` | `0.0350` | `0.0211` | `0.5474` | `315` | `687` | `143` | `57` |

结论：

- 重新对齐 benchmark 定义是必要的
- 但仅靠 free-generation prompt 还不够
- 这版 benchmark-aligned prompt 没有成为强基线

## 5. 当前阶段结论

截至 `2026-05-21`，可以确认的结论是：

1. `comparisons` evaluator 口径已经比旧版更干净，主指标解释可用。
2. benchmark 里的 comparison label 形态非常混合，不能简化成单一 pair 抽取问题。
3. `fewshot_fix` 只能减少 `extra`，不能稳定提高主恢复率。
4. constrained-selection 在 `dev20` 上可以显著提升，但当前 `v2` 没有泛化到 `test200`。
5. 单靠 benchmark-aligned free-generation prompt 也没有成为有效主路线。

## 6. 当前不该误判的点

这轮最容易误判的地方有两个：

1. 不能因为 `dev20` 上 constrained-selection v2 最好，就认为它已经可用。
   - `test200` 已经显示它当前不稳。
2. 不能因为 benchmark-aligned prompt 在定义上更正确，就认为它会自动提升主指标。
   - 实际 `dev80` / `test200` 结果并没有支持这一点。

## 7. 当前最值得保留的资产

虽然这轮还没有得到稳定主方案，但有三块资产已经沉淀下来：

1. 更干净的 `comparisons` evaluator
2. 对 benchmark comparison ontology 的更清楚认识
3. 一个在 `dev20` 上有信号、但尚未泛化的 constrained-selection 骨架

## 8. 关键产物位置

主要结果目录：

- `results/comparisons_dev20_20260521/`
- `results/comparisons_test200_20260521/`
- `results/comparisons_prompt_benchmark_20260521/`

关键子集：

- `dev20`：
  - `results/comparisons_dev20_20260521/conditional_splits/full-text/dev_comparisons_dev20.jsonl`
- `dev80`：
  - `results/comparisons_prompt_benchmark_20260521/conditional_splits/full-text/dev_comparisons_dev80.jsonl`
- `test200`：
  - `results/comparisons_test200_20260521/conditional_splits/full-text/test_comparisons_test200.jsonl`
  - `results/comparisons_prompt_benchmark_20260521/conditional_splits/full-text/test_comparisons_test200.jsonl`

关键评测文件：

- constrained-selection v2 `dev20`：
  - `results/comparisons_dev20_20260521/constrained_selection_v2_live/evaluations/gpt-5.4-mini/dev/comparisons/full-text/comparisons_constrained_selection_v1/aggregate.json`
- constrained-selection v2 `test200`：
  - `results/comparisons_test200_20260521/constrained_selection_v2_live/evaluations/gpt-5.4-mini/test/comparisons/full-text/comparisons_constrained_selection_v1/aggregate.json`
- benchmark-aligned prompt `dev80`：
  - `results/comparisons_prompt_benchmark_20260521/dev80_benchmark_prompt/evaluations/gpt-5.4-mini/dev/comparisons/full-text/comparisons_prompt_benchmark_aligned_v1/aggregate.json`
- benchmark-aligned prompt `test200`：
  - `results/comparisons_prompt_benchmark_20260521/test200_benchmark_prompt/evaluations/gpt-5.4-mini/test/comparisons/full-text/comparisons_prompt_benchmark_aligned_v1/aggregate.json`

## 9. 当前阶段建议起点

如果下一阶段只保留一个真正值得继续投入的方向，我建议保留：

- constrained-selection 这条大方向

原因不是当前版本已经成功，而是：

- 它在 `dev20` 上是唯一明显把主 F1 拉高的路线
- `v1 -> v2` 已经证明 candidate quality 是主要决定因素之一
- benchmark-aligned prompt 也更适合作为 selection 框架里的 instruction，而不是单独裸跑 free-generation
