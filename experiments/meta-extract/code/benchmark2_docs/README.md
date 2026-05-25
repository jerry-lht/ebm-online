# Benchmark2 Docs

当前正式执行依据：

- `benchmark2_item_evaluation_plan_v1.md`
- `benchmark2_official_item_support_experiment_record_20260520.md`

归档历史文档：

- `archive/benchmark2_timepoint_subgroup_evaluation_plan_v1.md`

## 当前实现状态

`benchmark2_item_evaluation_plan_v1.md` 已对应到当前 benchmark2-v2 正式实现。仓库主流程现为四任务框架，不再以旧三阶段脚本作为正式接口。

## 正式命令

数据准备：

- `code/bin/prepare-data --dataset-path ... --output-dir RUN_DIR/instances`

四任务运行：

- `code/bin/run-support --run-dir RUN_DIR --mode llm`
- `code/bin/run-proposal --run-dir RUN_DIR --mode llm`
- `code/bin/run-oracle-extraction --run-dir RUN_DIR --mode llm`
- `code/bin/run-routed-extraction --run-dir RUN_DIR --mode llm`

评分与报告：

- `code/bin/score-all --run-dir RUN_DIR`
- `code/bin/build-report --run-dir RUN_DIR --output-dir RUN_DIR/reports`
- `code/bin/rerun-failures --task proposal --run-dir RUN_DIR --mode llm`

## run_dir 结构

正式运行目录固定为：

- `instances/`
- `predictions/`
- `scores/`
- `reports/`
- `manifests/`
- `logs/`

同一 `run_dir` 下会落盘实例、预测、失败样本、summary、tables manifest、prompt/model/version 元数据，支持 resume 和失败重跑。

## Support 口径提醒

`Official Item Support` 的负标签需要保守解释。当前实现里，`not_supported` 通常表示该 official item 没携带 `subgroup` 或 `timepoints` 字段，不等于文章文本明确排除了该字段。后续分析请优先关注 supported-class recall、joint consistency，并把负例相关 accuracy / precision 放在 incomplete negative 的前提下解读。

Boundary 固定为：

- 泛泛出现的 follow-up / study duration / visit schedule 不自动支持 official timepoint
- 样本描述、纳入标准、一般性 population wording 不自动支持 official subgroup
- `uncertain` 仅允许证据不足、timepoint 粒度不匹配、或多重 plausible interpretation

## 当前阶段切换

`Official Item Support` 已完成一轮阶段性迭代，当前冻结版本为 `split-support v1`。timepoint 更宽松规则的后续实验未被保留，因为它会提升部分 recall 但损伤整体 `joint_support_consistency`。

当前默认工作重心转向下一阶段：`Open-world Item Proposal`。
