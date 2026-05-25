# Benchmark2 `analysis item` 对齐版实验设计（v2, 已拍板实现）

## 0. 当前正式默认

本方案现已作为 benchmark2-v2 正式实现落地。默认决策如下：

- 不保留旧三阶段 CLI 兼容入口
- 每次运行使用独立 `run_dir`
- 正式四实验固定为：
  - `Official Item Support`
  - `Open-world Item Proposal`
  - `Oracle Extraction`
  - `Routed Extraction`
- analysis setting 采用：
  - `outcome_concept + comparison + data_type + effect_measure`
- `subgroup = null` 为合法值
- `timepoints` 允许 list，并在 routed extraction 中显式预测
- 当前默认主证据模式为 `full-text`

## 1. 四实验正式输出 schema

### Official Item Support

```json
{
  "subgroup_support_status": "supported | not_supported | uncertain",
  "timepoint_support_status": "supported | not_supported | uncertain"
}
```

口径固定：

- `supported`：证据明确把 official subgroup / official timepoint 绑定到当前分析结果
- `not_supported`：当前证据不足以支持该 official 字段属于当前分析结果
- `uncertain`：仅用于证据不足、timepoint 粒度不匹配、或存在多个 plausible interpretation

解释约束：

- support 负标签需要保守解释，通常表示该 official item 未携带该字段，而不等于文章文本明确证明该字段不存在
- follow-up timing、study duration、visit schedule 的泛泛出现不自动支持 official timepoint
- 样本描述、纳入标准、一般性 population wording 不自动支持 official subgroup
- official subgroup 即使长得像 comparison/duration/label，也先视为待验证字段，不能因为形式不典型而直接否定

`uncertain` 只允许以下原因：

1. 文本证据不足
2. 只能支持更粗粒度的 timepoint
3. 存在多个 plausible interpretation

### Official Item Support 当前阶段结论

当前 support 实验已完成一次 prompt 结构重构与两轮小规模真实对比，当前拍板如下：

- 正式保留 `split-support v1`：subgroup 与 timepoint 分两次 prompt 调用，再合并为统一 prediction row
- 不保留 timepoint 更宽松规则的实验版本；该版本虽提升部分 timepoint recall，但会明显引入更多 `not_supported -> supported` 错误，并拉低 joint consistency
- 当前 support 任务暂不继续做 prompt 细调，后续如需回访，优先从 `timepoint supported -> not_supported` 的定向错例出发，而不是整体放宽 boundary
- 当前项目节奏转向下一阶段 `Open-world Item Proposal`

### Open-world Item Proposal

```json
{
  "proposed_items": [
    {"subgroup": "string|null", "timepoints": ["string"]}
  ]
}
```

### Oracle Extraction

```json
{
  "predicted_rows": [
    {
      "direct_extraction_fields": [
        {"field": "...", "value": "..."}
      ]
    }
  ]
}
```

### Oracle Extraction 当前阶段结论

截至 2026-05-21，`Oracle Extraction` 已完成一轮正式 baseline 和一轮 row-alignment prompt probe。当前拍板如下：

- 正式工作版 prompt 变体保留 `results_slice_few_shot`
- 当前 full `dev` baseline 记录见：
  - `results/oracle_dev_baseline_results_slice_fewshot_20260521/`
  - `results/oracle_dev_baseline_results_slice_fewshot_v2_20260521/`
- 当前阶段实验记录汇总见：
  - `code/benchmark2_docs/benchmark2_oracle_extraction_experiment_record_20260521.md`
- 当前默认不继续细调 `Oracle Extraction` prompt
- 若后续回访：
  1. 优先继续做 `Dichotomous`
  2. `Continuous` 先限制在 `all_present` 子集上分析
  3. `Contrast level` 暂不作为主要优化方向

### Routed Extraction

```json
{
  "predicted_items": [
    {
      "subgroup": "string|null",
      "timepoints": ["string"],
      "predicted_rows": [
        {
          "direct_extraction_fields": [
            {"field": "...", "value": "..."}
          ]
        }
      ]
    }
  ]
}
```

## 2. 正式实例文件

`prepare-data` 现在固定输出：

- `support_instances.jsonl`
- `proposal_instances.jsonl`
- `oracle_extraction_instances.jsonl`
- `routed_extraction_instances.jsonl`
- `split_manifest.json`
- `prepare_data_summary.json`

## 3. 正式 CLI

正式入口固定为：

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

`mode` 的正式叙事仅保留 `llm`；`oracle` 和 `empty` 仅用于测试与回归。

## 4. 评分口径

### Official Item Support

报告：

- subgroup accuracy
- timepoint accuracy
- subgroup macro-F1
- timepoint macro-F1
- supported-class recall
- `uncertain_rate`
- `joint_support_consistency`

并显式注明 negative incomplete 的保守解释。

### Open-world Item Proposal

报告：

- subgroup precision/recall/F1
- timepoint precision/recall/F1
- structured proposal precision/recall/F1
- `supported_extra_count`
- `unsupported_extra_count`
- `conflicting_extra_count`

### Oracle Extraction

主分只看 `direct_extraction_fields`，报告：

- field precision/recall/F1
- row precision/recall/F1
- `row_exact_match`
- `item_exact_match`
- `complete_row_rate`
- `empty_prediction_rate`
- `per_data_type`
- `per_field`
- `per_match_status`

其中 `unique` 与 `multiple` 进入主分，`no_match` 不进入主分。

### Routed Extraction

报告：

- proposal 层 subgroup/timepoint/structured precision/recall/F1
- end-to-end field precision/recall/F1
- end-to-end row precision/recall/F1
- `setting_success_rate`
- 误差桶：
  - `routing_missing_count`
  - `routing_extra_count`
  - `timepoint_misalignment_count`
  - `extraction_error_count`
  - `pipeline_propagation_error_count`

## 5. 运行目录协议

每次运行使用独立 `run_dir`，结构固定为：

- `instances/`
- `predictions/`
- `scores/`
- `reports/`
- `manifests/`
- `logs/`

框架保证：

- resume
- failed instance 落盘
- rerun failures
- run summary
- atomic summary/manifest write
- parse failure 写空预测并保留错误统计

## 6. 当前实现范围

当前正式 baseline 仅保留 `LLM-only` 接口位；同时保留 `oracle` / `empty` 作为测试回归能力。

`abstract-only` 仍只保留接口扩展位，本轮不另起第二套正式流水线。
