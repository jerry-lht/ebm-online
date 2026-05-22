# Official Item Support 实验记录（2026-05-20）

## 目的

本记录用于沉淀 benchmark2-v2 第一阶段 `Official Item Support` 的真实实验数据、阶段结论、已验证/已放弃方案，以及后续回访优化入口。该文档是本阶段结果的集中记录，不替代正式方案文档，但用于避免实验信息只散落在对话和结果目录中。

## 当前阶段结论

当前阶段已决定：

- 暂停继续迭代 `Official Item Support`
- 当前冻结的较优实现为 `split-support v1`
- `timepoint` 更宽松规则实验版不保留
- 当前项目重心切换到下一阶段 `Open-world Item Proposal`

## 口径说明

### Support 负标签解释

`Official Item Support` 的 `not_supported` 需要保守解释。当前 benchmark2-v2 实现里，support gold 来自 official item 是否携带 `subgroup` / `timepoints` 字段：

- official item 有 `subgroup` -> `subgroup_support_status = supported`
- official item 无 `subgroup` -> `subgroup_support_status = not_supported`
- official item 有 `timepoints` -> `timepoint_support_status = supported`
- official item 无 `timepoints` -> `timepoint_support_status = not_supported`

因此 support 负标签通常表示“该 official item 未承载该字段”，而不等于“文章文本明确证明该字段不存在”。本阶段所有 accuracy / precision 相关指标都需要在 incomplete negative 的前提下解释。

### Boundary

当前保留的 boundary 是：

- `supported`：证据明确把 official subgroup / official timepoint 绑定到当前分析结果
- `not_supported`：当前证据不足以支持该 official 字段属于当前分析结果
- `uncertain`：仅允许文本证据不足、timepoint 粒度不匹配、或存在多个 plausible interpretation

额外约束：

- 泛泛出现的 follow-up / study duration / visit schedule 不自动支持 official timepoint
- 样本描述、纳入标准、一般性 population wording 不自动支持 official subgroup
- official subgroup 即使长得像 comparison/duration/label，也先视为待验证字段

## 实验运行记录

### Run A: joint support, `gpt-5.4-mini`, full dev

路径：
- `results/support_dev_llm_20260520/`

规模：
- `dev instances = 888`

主指标：
- `subgroup_accuracy = 0.6577`
- `timepoint_accuracy = 0.6374`
- `subgroup_macro_f1 = 0.4518`
- `timepoint_macro_f1 = 0.4363`
- `subgroup_supported_recall = 0.5269`
- `timepoint_supported_recall = 0.6637`
- `uncertain_rate = 0.1779`
- `joint_support_consistency = 0.4032`

结论：
- 作为 joint baseline 可用
- `subgroup` 明显偏漏报
- `timepoint` 更容易 over-predict / over-uncertain
- `joint_support_consistency` 偏低，是继续优化的主要动机

### Run B: smoke demo, `gpt-5-mini`

路径：
- `results/support_demo_gpt5mini_20260520/`

规模：
- `dev instances = 6`

主指标：
- `joint_support_consistency = 1.0`

说明：
- 该 run 只用于链路 smoke test
- 样本过小，不作为模型质量判断依据

### Run C: full dev, `gpt-5-mini`, provider stress run

路径：
- `results/support_full_gpt5mini_20260520/`

规模：
- `dev instances = 888`

运行观察：
- 出现大量 provider-side 错误
- 已确认错误不主要是 JSON 脏输出，而是 provider 返回：
  - `503 model_not_found`
  - `403 User has been banned`
  - 少量 `524`

结论：
- 该 run 不适合作为 support 质量的正式对照结果
- 可用于观察 provider 稳定性，不适合作为 prompt 优化结论依据

### Run D: split-support v1 probe, `gpt-5.4-mini`, 80 dev

路径：
- `results/support_split_probe_gpt54mini_20260520/`

规模：
- `instances = 80`
- `support_call_mode = split`
- `parse_errors = 0`
- `json_repair_attempted = 0`

主指标：
- `subgroup_accuracy = 0.7125`
- `timepoint_accuracy = 0.8500`
- `subgroup_macro_f1 = 0.4725`
- `timepoint_macro_f1 = 0.5133`
- `subgroup_supported_recall = 0.5238`
- `timepoint_supported_recall = 0.5000`
- `uncertain_rate = 0.0875`
- `joint_support_consistency = 0.6625`

同 80 条 joint baseline 对照：
- `subgroup_accuracy`: `0.6250 -> 0.7125`
- `timepoint_accuracy`: `0.6625 -> 0.8500`
- `subgroup_supported_recall`: `0.3810 -> 0.5238`
- `timepoint_supported_recall`: `0.7857 -> 0.5000`
- `uncertain_rate`: `0.3250 -> 0.0875`
- `joint_support_consistency`: `0.4875 -> 0.6625`

结论：
- `split-support` 架构优于 joint support
- subgroup 改善明显
- timepoint 更干净，但更保守，recall 有下降
- 当前阶段选择保留该版本

### Run E: split-support v2（timepoint relaxed）probe, `gpt-5.4-mini`, 80 dev

路径：
- `results/support_split_probe_gpt54mini_tp2_20260520/`

规模：
- `instances = 80`
- `support_call_mode = split`
- `parse_errors = 0`
- `json_repair_attempted = 0`

主指标：
- `subgroup_accuracy = 0.6625`
- `timepoint_accuracy = 0.7500`
- `subgroup_macro_f1 = 0.4373`
- `timepoint_macro_f1 = 0.4364`
- `subgroup_supported_recall = 0.5000`
- `timepoint_supported_recall = 0.5714`
- `uncertain_rate = 0.0250`
- `joint_support_consistency = 0.5375`

相对 split-support v1：
- `timepoint_supported_recall`: `0.5000 -> 0.5714`
- 但 `timepoint_accuracy`: `0.8500 -> 0.7500`
- `joint_support_consistency`: `0.6625 -> 0.5375`
- `subgroup_accuracy`: `0.7125 -> 0.6625`

错误变化：
- `timepoint not_supported -> supported` 明显增多
- false positive 回潮

结论：
- timepoint 更宽松规则实验版不保留
- 该方向会提升部分 recall，但损伤整体 joint consistency

## 阶段结论汇总

### 保留项

- 保留 `split-support v1`
- 保留 support 负标签的保守解释口径
- 保留较严格的 timepoint boundary，不整体放宽

### 不保留项

- 不保留 `timepoint relaxed` 版本
- 不以 `gpt-5-mini + tokenrun` 的 full run 作为正式质量结论依据

### 已知问题

- `split-support v1` 下，timepoint 仍偏保守，存在 `supported -> not_supported` 漏报
- subgroup 在 `Continuous` / `Contrast level` 的小桶上仍不稳定
- provider 稳定性会显著影响 live run 结果，尤其在 `gpt-5-mini` 和较高并发下

## 后续回访建议

如果后续重新回到 `Official Item Support`，建议顺序为：

1. 基于 `split-support v1`，只抽 `timepoint supported -> not_supported` 的定向错例
2. 做更窄的 timepoint 正例规则，而不是整体放宽 boundary
3. 保持 `subgroup` prompt 基本不动，优先避免回退 subgroup 改善
4. live run 优先使用当前更稳定的 provider/model 组合，不再依赖不稳定通道做结论

## 下一阶段

当前默认推进到：

- `Open-world Item Proposal`

本阶段结束时，不再继续对 `Official Item Support` 做 prompt 细调。后续若回访，以本记录为起点。
