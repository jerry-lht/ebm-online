# Meta-Extract Benchmark2-v2

这个目录当前提供一套面向 `benchmark2-v2` 的最小可运行实验框架，覆盖 4 个任务：

- `support`: 判断官方 item 的 subgroup / timepoint 是否被文中支持
- `proposal`: 开放式提出 setting 对应的 subgroup / timepoint item
- `oracle_extraction`: 在官方 item 已知时抽取 direct fields
- `routed_extraction`: 先提出 item，再按 item 抽取 direct fields

## 目录结构

- `code/meta_extract/`: 核心 Python 模块
- `code/bin/`: CLI 入口
- `code/tests/`: 单元测试和闭环 smoke tests
- `data/meta_analysis_data_extraction_v1/`: benchmark 数据
- `results/`: 建议放实验输出

## Dev/Test 划分

发布数据不带官方 `dev/test` split。当前 `prepare-data` 会在 review 级别生成可复现切分：

- 默认 `split_seed=meta-extract-benchmark2-v2-split-v1`
- 默认 `dev_fraction=0.2`
- 同一 `review_id` 不会同时落到 `dev` 和 `test`
- 输出 `split_manifest.json` 和 `prepare_data_summary.json`

所有实例文件都带 `split` 字段。

`--max-settings` 的行为需要特别注意：

- 不带 `--target-split` 时，`--max-settings` 仍然按数据集顺序截断，可能混入 `dev` 和 `test`
- 带 `--target-split dev` 或 `--target-split test` 时，会先按 split 过滤，再应用 `--max-settings`

## CLI

主入口：

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

辅助入口：

- `llm-ping`
- `rerun-failures`

运行前建议显式设置：

```bash
PYTHONPATH=code
```

Python 环境示例：

```text
/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python
```

默认模型由运行环境配置决定，当前代码会走 `default_model_name()`。

## Run Directory Layout

建议所有任务共享一个 `run_dir`，目录结构如下：

- `instances/`
- `predictions/`
- `scores/`
- `reports/`
- `manifests/`
- `logs/`

各 task 默认会在该目录下读写对应文件名，例如：

- `instances/proposal_instances.jsonl`
- `predictions/proposal_predictions.jsonl`
- `scores/proposal_summary.json`
- `manifests/proposal_run_manifest.json`

## Quick Start

### 1. 准备实例

完整实例：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/prepare-data \
  --dataset-path data/meta_analysis_data_extraction_v1/benchmark.jsonl \
  --output-dir results/benchmark2_demo/instances
```

构造 `dev-only 80` proposal probe：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/prepare-data \
  --dataset-path data/meta_analysis_data_extraction_v1/benchmark.jsonl \
  --output-dir results/proposal_probe_dev80/instances \
  --target-split dev \
  --max-settings 80
```

产物：

- `support_instances.jsonl`
- `proposal_instances.jsonl`
- `oracle_extraction_instances.jsonl`
- `routed_extraction_instances.jsonl`
- `split_manifest.json`
- `prepare_data_summary.json`

### 2. 运行 Support

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/run-support \
  --run-dir results/benchmark2_demo \
  --split dev \
  --mode llm \
  --prompt-variant default
```

### 3. 运行 Proposal

baseline：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/run-proposal \
  --run-dir results/proposal_probe_dev80 \
  --split dev \
  --mode llm \
  --prompt-variant negative_examples
```

当前已实现的 proposal 变体包括：

- `default`
- `negative_examples`
- `negative_examples_ebm`
- `negative_examples_split`

其中：

- `negative_examples_ebm` 用更严格的 EBM / Cochrane 风格语义约束 subgroup、analysis population、treatment arm、follow-up label 的区分
- `negative_examples_split` 内部会拆成 subgroup proposal 和 timepoint proposal 两次调用，再保守合并回公开的 `proposed_items` schema

### 4. 运行 Oracle Extraction

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/run-oracle-extraction \
  --run-dir results/benchmark2_demo \
  --split dev \
  --mode llm
```

### 5. 运行 Routed Extraction

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/run-routed-extraction \
  --run-dir results/benchmark2_demo \
  --split dev \
  --mode llm
```

### 6. 分任务评分

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/score-support --run-dir results/benchmark2_demo
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/score-proposal --run-dir results/benchmark2_demo
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/score-oracle-extraction --run-dir results/benchmark2_demo
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/score-routed-extraction --run-dir results/benchmark2_demo
```

### 7. 一次性评分

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/score-all \
  --run-dir results/benchmark2_demo
```

### 8. 生成报告

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python code/bin/build-report \
  --run-dir results/benchmark2_demo
```

## 主要评分口径

### Support

主结果位于 `support_summary.json`：

- `primary_metrics`
- `per_data_type`
- `error_buckets`

### Proposal

主结果位于 `proposal_summary.json`：

- `primary_metrics`: 严格全量口径的 subgroup / timepoint / structured PRF
- `observed_primary_metrics`: 仅对 benchmark 已观察到的 subgroup / timepoint / structured 统计
- `observed_counts`: observed-only 分母
- `error_buckets`: 当前包含 `supported_extra_count`、`unsupported_extra_count`、`conflicting_extra_count`

当前 caveats：

- `supported_extra_count` 仍未实现，当前固定写为 `0`，不能按可解释指标使用
- proposal 现在同时输出 strict full metrics 和 observed-only metrics，比较实验时应同时看两组结果

### Oracle Extraction

主结果位于 `oracle_extraction_summary.json`：

- `primary_metrics`
- `per_data_type`
- `per_field`
- `per_match_status`

### Routed Extraction

主结果位于 `routed_extraction_summary.json`：

- `primary_metrics`
- `per_data_type`
- `error_buckets`

## 典型 Proposal 实验流程

以 `dev-only 80` probe 为例：

1. `prepare-data --target-split dev --max-settings 80` 生成 split-correct probe。
2. 分别运行 `negative_examples`、`negative_examples_ebm`、`negative_examples_split`。
3. 用同一个 scorer 版本运行 `score-proposal`。
4. 主选择指标优先看 `primary_metrics.structured.f1`，再看 `conflicting_extra_count`、`observed_primary_metrics.structured.f1` 和 run health。


## 当前状态

### Proposal 现状同步

截至 2026-05-21，proposal 的最新结论如下：

- `dev-only 80` probe 上，`negative_examples_ebm` 是当前最优 proposal 变体
- 该变体在 dev probe 上的主指标为：
  - `strict structured`: precision `0.3657`, recall `0.6125`, F1 `0.4579`
  - `strict subgroup`: precision `0.4328`, recall `0.7250`, F1 `0.5421`
  - `strict timepoint`: precision `0.2000`, recall `0.6000`, F1 `0.3000`
  - `conflicting_extra_count = 81`
- 但在 `test` 全量 `3382` setting 上，`negative_examples_ebm` 明显退化：
  - `strict structured`: precision `0.1409`, recall `0.1919`, F1 `0.1625`
  - `strict subgroup`: precision `0.2615`, recall `0.3561`, F1 `0.3015`
  - `strict timepoint`: precision `0.0653`, recall `0.1836`, F1 `0.0964`
  - `conflicting_extra_count = 4138`
- 因此当前判断是：proposal 仍存在明显 over-proposal / boundary-control 问题，不应继续直接扩大 proposal test 运行。

### 下一阶段建议

proposal 后面的下一块工作应该优先转到 `oracle_extraction`，而不是继续扩 proposal 或直接做 routed end-to-end。

原因：

- `oracle_extraction` 可以隔离评估：当官方 item 已知正确时，direct field 抽取本身到底行不行
- 如果直接做 `routed_extraction`，proposal 错误会污染 extraction 判断
- 只有先看清 extraction 上限，后面 proposal / routed 的改动才有解释力

推荐顺序：

1. 先梳理 `oracle_extraction` 当前 baseline 和已有结果。
2. 在 `dev` 上定位 extraction 的主要错误类型：
   - 字段漏抽
   - 字段名不规范
   - row-level 合并/拆分错误
   - Contrast level 条件可抽字段错误
3. 在 item 已知正确的前提下，把 extraction 本身调稳。
4. 之后再回到 `routed_extraction`，把 proposal 和 extraction 串起来。

### Oracle Extraction 现状同步

截至 2026-05-21，`oracle_extraction` 已完成当前阶段的 baseline 与 prompt probe，阶段记录见：

- `code/benchmark2_docs/benchmark2_oracle_extraction_experiment_record_20260521.md`

当前冻结结论：

- 正式工作版 prompt 变体为 `results_slice_few_shot`
- full `dev` baseline v1 路径：`results/oracle_dev_baseline_results_slice_fewshot_20260521/`
- full `dev` baseline v2 路径：`results/oracle_dev_baseline_results_slice_fewshot_v2_20260521/`
- v2 相对 v1 的变化是：`row_f1` 和 `item_exact_match` 略升，但 `field_f1` 下降，`empty_prediction_rate` 明显升高
- 当前判断是：`Oracle Extraction` 的主要问题不只是 prompt，还包括 source coverage 不足，以及 `Continuous` / `Contrast level` 与源文本表达层级的错位
- 当前默认先停止继续细调 `oracle_extraction` prompt，后续若回访，优先拆开处理 `Dichotomous` 与 `Continuous`

## 备注

- `rerun-failures` 可基于 `run_dir` 对失败实例重跑。
- 如果只想确认 LLM 通路是否联通，可使用 `llm-ping`。
