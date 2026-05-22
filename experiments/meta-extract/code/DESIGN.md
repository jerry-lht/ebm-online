# Benchmark2-v2 任务注册式实验框架

当前实现已从旧三阶段流程切换为 benchmark2-v2 的正式四任务框架，核心目标是让实例构建、预测执行、评分和报告围绕统一任务协议演化，而不是继续复制 stage1/stage2/stage3 风格脚本。

## 正式任务

当前正式任务固定为四个：

- `support`: Official Item Support
- `proposal`: Open-world Item Proposal
- `oracle_extraction`: Oracle Extraction
- `routed_extraction`: Routed Extraction

每个任务在注册表中固定声明：

- 实例文件名
- 预测文件名
- 运行汇总文件名
- 失败实例文件名
- 评分文件名
- summary 文件名
- report section 类型

## 运行目录协议

每次运行使用独立 `run_dir`，目录结构固定为：

- `instances/`
- `predictions/`
- `scores/`
- `reports/`
- `manifests/`
- `logs/`

其中：

- `instances/` 保存四任务实例文件、`split_manifest.json` 和 `prepare_data_summary.json`
- `predictions/` 保存任务预测 JSONL、`*_run_summary.json` 和 `*_failed_instances.jsonl`
- `scores/` 保存 instance-level score JSONL 和任务 summary JSON
- `reports/` 保存四实验表格、markdown 报告和 `tables_manifest.json`
- `manifests/` 保存 run config、task config、prompt/model/version 元数据

## 运行时保证

runner 将工程约束做成正式协议：

- `resume`: 基于 prediction JSONL 的 `instance_id` 去重恢复
- `flush-every`: 通过逐条落盘避免长任务中断丢结果
- `failed_instances.jsonl`: 单独记录真实运行失败样本
- `rerun-failures`: 从失败文件筛选实例并重跑
- `max-attempts`: 控制单实例最大尝试次数
- `continue-on-error`: 默认不中断整批任务
- `run_summary.json`: 每次运行结束立即写汇总
- `atomic summary write`: summary 和 manifest 使用原子写入

注意：prediction schema 解析失败不会抛弃实例。预测器会写空预测，并在 `prediction_stats.parse_error` 中记录错误，保证后续 scorer 和报告仍可稳定读取。

## 数据与 schema

`prepare-data` 现在固定输出：

- `support_instances.jsonl`
- `proposal_instances.jsonl`
- `oracle_extraction_instances.jsonl`
- `routed_extraction_instances.jsonl`
- `split_manifest.json`
- `prepare_data_summary.json`

当前 analysis setting 采用：

`(review, study, outcome_concept, comparison, data_type, effect_measure)`

并显式允许：

- `subgroup = null`
- `timepoints = list[str]`
- `full-text` 为默认 `evidence_mode`

## 正式 CLI

旧 CLI `run-stage1-routing`、`run-stage2-extraction`、`run-stage3-end2end`、`score-results` 已不再作为正式接口。

当前正式入口：

- `prepare-data`
- `run-support`
- `run-proposal`
- `run-oracle-extraction`
- `run-routed-extraction`
- `score-support`
- `score-proposal`
- `score-oracle-extraction`
- `score-routed-extraction`
- `score-all`
- `build-report`
- `rerun-failures`

所有 `run-*` 命令统一支持：

- `--instances-path`
- `--run-dir` 或 `--output-dir`
- `--split`
- `--mode`
- `--prompt-variant`
- `--resume`
- `--num-workers`
- `--flush-every`
- `--continue-on-error`
- `--max-attempts`
- `--no-progress`

## Support Label Interpretation

`Official Item Support` 中的 `not_supported` 需要保守解释。当前 benchmark2-v2 实现里，support gold 来自 official item 自身是否携带 `subgroup` / `timepoints` 字段：

- official item 有 `subgroup` -> `subgroup_support_status = supported`
- official item 无 `subgroup` -> `subgroup_support_status = not_supported`
- official item 有 `timepoints` -> `timepoint_support_status = supported`
- official item 无 `timepoints` -> `timepoint_support_status = not_supported`

因此 support 负标签通常表示“该 official item 未承载该字段”，而不等于“文章文本明确证明该字段不存在”。后续分析和报告必须把 support negatives 视为 incomplete negatives，并保守解释相关 accuracy / precision。

`Official Item Support` 的 boundary 固定如下：

- `supported`：证据明确把 official subgroup 或 official timepoint 绑定到当前分析结果
- `not_supported`：当前证据不足以支持该 official 字段属于当前分析结果
- `uncertain`：仅允许文本证据不足、timepoint 粒度不匹配、或存在多个 plausible interpretation

其中：

- 泛泛出现 follow-up timing、study duration、visit schedule，不自动支持 official timepoint
- 样本描述或纳入标准，不自动支持 official subgroup
- official subgroup 即使形式上像 comparison/duration/label，也必须先作为待验证字段处理

## Current Support Status

`Official Item Support` 当前已完成一轮阶段性迭代，并决定暂时停止继续调 prompt，先转入下一阶段实验。当前结论固定如下：

- 当前较优实现为 `split-support`：`subgroup` 与 `timepoint` 分两次 prompt 调用，再合并回同一 prediction schema
- `split-support` 相比 joint support，在小规模真实实验中显著提升了 `joint_support_consistency`、`subgroup_accuracy`、`subgroup_supported_recall`，并明显降低了 `uncertain_rate`
- 针对 `timepoint` 做的第二轮“更宽松支持判定”实验没有保留价值：虽然拉高了 `timepoint_supported_recall`，但明显损伤了 `timepoint_accuracy` 与整体 `joint_support_consistency`
- 因此当前冻结的 support 策略为：保留 `split-support v1`，不采用更宽松的 timepoint 规则

后续允许回到 support 任务继续优化，但在当前里程碑中，优先推进下一阶段 `Open-world Item Proposal`。

## 评分与报告

四个任务各自产出：

- instance-level score JSONL
- task-level summary JSON

summary 外层协议尽量统一：

- `task`
- `instances`
- `scored_instances`
- `primary_metrics`
- `per_data_type`
- `error_buckets`
- `representative_failures`
- `run_metadata`

`build-report` 现在输出四实验主表、per-data-type、per-field、per-match-status、error buckets、representative failures 和 `report.md`。
