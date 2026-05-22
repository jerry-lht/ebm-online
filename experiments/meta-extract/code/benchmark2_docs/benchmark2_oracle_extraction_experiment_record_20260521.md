# Oracle Extraction 实验记录（2026-05-21）

## 目的

本记录用于沉淀 benchmark2-v2 第二阶段 `Oracle Extraction` 的当前实验状态、baseline 结果、失败归因和当前冻结结论。该文档只记录 `official item -> predicted_rows` 任务，不覆盖 `proposal` 或 `routed_extraction`。

## 当前阶段结论

截至 2026-05-21，当前阶段已决定：

- 暂停继续细调 `Oracle Extraction` prompt
- 当前冻结 baseline 以 `results_slice_few_shot` 为正式工作版
- `Contrast level` 暂不作为继续优化重点
- 后续若回访，优先分别处理 `Dichotomous` 与 `Continuous`

## 任务口径

当前 `oracle_extraction` 的正式任务定义是：

- 任务单位是 `official analysis item`
- 输出目标是“当前 official item 对应的一个或多个 study direct rows”
- `setting_context` 只是 disambiguation context，不是抽取目标本身

当前 prompt payload 的核心字段是：

- `study`
- `setting_context`
- `official_item`
- `task_target`
- `allowed_direct_fields`
- `evidence_sections`
- `evidence_tables`
- `output_schema`

当前正式工作版 prompt 采用：

- `prompt_variant = results_slice_few_shot`
- 输入切片只保留 `abstract + results sections + tables`
- 不再向 `oracle_extraction` 喂 `Introduction / Methods / Discussion`

## Source Coverage 审计

为区分“模型没抽出来”和“当前 source 根本不包含 gold 数值”，本阶段增加了 source coverage 审计：

- 脚本：`code/bin/audit-oracle-source-coverage`
- 输出目录：`results/oracle_source_coverage_dev_20260521/`

`dev` 全量 `888` 条的 coverage 计数如下：

- `all_gold_numeric_values_present = 406`
- `partial_gold_numeric_values_present = 382`
- `no_gold_numeric_values_present = 52`
- `no_gold_numeric_values = 48`

这说明在当前 `study.full_content` 视角下，只有约 `45.7%` 的 `dev` 实例满足“gold 数值都能在 source 中找到”。因此全量 `oracle_extraction` 指标不能简单解释为纯 prompt / 模型能力。

## 已跑实验

### Run A: full dev baseline v1

路径：
- `results/oracle_dev_baseline_results_slice_fewshot_20260521/`

配置：
- `split = dev`
- `mode = llm`
- `prompt_variant = results_slice_few_shot`
- `num_workers = 32`

规模：
- `instances = 888`
- `failure_count = 0`

主指标：
- `field_f1 = 0.2740`
- `row_f1 = 0.1239`
- `item_exact_match = 0.1214`
- `empty_prediction_rate = 0.2060`

按 `data_type`：
- `Dichotomous`: `field_f1 = 0.4428`, `row_f1 = 0.1973`, `item_exact_match = 0.2013`
- `Continuous`: `field_f1 = 0.1165`, `row_f1 = 0.0243`, `item_exact_match = 0.0225`
- `Contrast level`: `field_f1 = 0.0233`, `row_f1 = 0.0000`, `item_exact_match = 0.0000`

### Run B: continuous present-only probe

路径：
- `results/oracle_dev_continuous_present_results_slice_fewshot_20260521/`

实例子集：
- `results/oracle_dev_continuous_present_subset_20260521.jsonl`

说明：
- 只保留 `Continuous` 中 `gold` 数值全部能在当前 source 找到的样本
- 用于验证 continuous 失败里到底有多少是 coverage 问题

规模：
- `instances = 12`

主指标：
- `field_f1 = 0.3676`
- `row_f1 = 0.1739`
- `item_exact_match = 0.1667`
- `empty_prediction_rate = 0.0833`

结论：
- `Continuous` 全量全灭不只是 prompt 问题
- 当 source 中确实有 gold 数值时，prompt 仍可恢复部分信号
- 但 `mean / SD / N` 的同一 row block 对齐仍然明显不稳

### Run C: full dev baseline v2（row-alignment prompt 调整后）

路径：
- `results/oracle_dev_baseline_results_slice_fewshot_v2_20260521/`

配置：
- `split = dev`
- `mode = llm`
- `prompt_variant = results_slice_few_shot`
- `num_workers = 32`
- few-shot 中额外强化了：
  - `Dichotomous` 的 row disambiguation
  - `Continuous` 的 `mean / SD / N` 同 row block 约束

规模：
- `instances = 888`
- `failure_count = 0`

主指标：
- `field_f1 = 0.2636`
- `row_f1 = 0.1382`
- `item_exact_match = 0.1286`
- `empty_prediction_rate = 0.2845`

按 `data_type`：
- `Dichotomous`: `field_f1 = 0.4344`, `row_f1 = 0.2288`, `item_exact_match = 0.2141`
- `Continuous`: `field_f1 = 0.1185`, `row_f1 = 0.0245`, `item_exact_match = 0.0225`
- `Contrast level`: `field_f1 = 0.0482`, `row_f1 = 0.0000`, `item_exact_match = 0.0000`

相对 v1：
- overall `row_f1`: `0.1239 -> 0.1382`
- overall `item_exact_match`: `0.1214 -> 0.1286`
- overall `field_f1`: `0.2740 -> 0.2636`
- overall `empty_prediction_rate`: `0.2060 -> 0.2845`

结论：
- row-level alignment 略有改善
- 但代价是显著更保守，空预测率上升
- 这轮 prompt 调整不构成整体 baseline 提升

## 问题归因

当前 `Oracle Extraction` 的主要问题不是单一原因，而是以下几层叠加：

### 1. Source coverage / 证据覆盖不全

- 全量 `dev` 中只有 `406 / 888` 满足 `all_present`
- 因此大量失败并不能直接归因于 prompt
- 特别是 `Continuous`，不少样本的 gold 值在当前 `study.full_content` 中并不完整可见

### 2. 任务定义与原文表达层级错位

- `Contrast level` gold 常要求规范化后的 effect-level 字段
- 原文给的是 `HR + CI` 或其他 effect 表达
- 这类样本本质上是 `extraction + transform`，而不只是 direct row extraction

### 3. Prompt / 模型的 row-level 对齐能力不足

- `Dichotomous` 经常能抽出结构完整的四元组，但属于错误 outcome row / subgroup / comparison
- `Continuous` 经常只能锁到大概位置，却拿不稳 `mean / SD / N` 的同一 row block

### 4. 上游表格或全文表示质量可能仍有限

- 当前证据足以说明“source 里并不总有 gold 所依赖的数值”
- 但尚不足以严格证明主要问题一定来自 OCR / table parsing
- 更可能是 supplementary 缺失、规范化字段未回写、或 benchmark 表示层与源文本不一致共同导致

## 分类型结论

### Dichotomous

当前更像是 `row selection / arm-value mapping` 问题，而不是“文章里没数据”。

观察：
- baseline 已经能稳定产出完整 row
- 但经常选错同表中的邻近 outcome row，或把 cases / N 对错 arm
- v2 prompt 能把 `row_f1` 拉高一点，但会明显增加空预测

当前判断：
- `Dichotomous` 仍然是最值得继续做 prompt 优化的桶
- 但本轮先冻结，不继续迭代

### Continuous

当前同时存在 coverage 问题和 extraction 问题。

观察：
- 只看 `all_present` 子集时，指标明显高于全量
- 但即使 source 足够，`mean / SD / N` 的同 row block 抽取仍然弱
- 常见现象是 `N` 相对更容易抽对，`mean / SD` 明显更差

当前判断：
- `Continuous` 不能仅靠继续改 wording 来解决
- 后续如果回访，应先把 `all_present` 与非 `all_present` 分开分析

### Contrast level

当前不作为继续优化重点。

原因：
- 问题已超出 direct row extraction 的简单 prompt 范畴
- 在继续做 routed 或 end-to-end 前，先冻结更合理

## 当前冻结结论

截至 2026-05-21，`Oracle Extraction` 当前阶段冻结结论如下：

- 保留 `results_slice_few_shot` 作为正式工作版 prompt 变体
- 不继续做 prompt 微调
- `dev` baseline 结果以 v1 / v2 两个 full run 共同作为阶段记录
- 后续若回访：
  1. 优先单独处理 `Dichotomous`
  2. `Continuous` 先基于 `all_present` 子集做开发
  3. `Contrast level` 暂不进入下一轮主要优化范围

