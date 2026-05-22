# Abstract + SR Info Analysis Setting Experiment

最小实验实现，目标是评估在仅使用 `SR-level 信息 + included study abstracts` 的条件下，模型能否直接生成 review-level 的 meta-analysis `analysis settings`。

当前实现覆盖：

- `prepare-data`: 从 benchmark 构造 abstract-only 输入，并生成 `dev/test` split
- `run`: 按 `model x split x review` 粒度并行运行，单 review 独立状态落盘
- 运行中实时输出进度条，并持续写入 `progress.json`，不会等到全部结束才汇总
- `evaluate`: 程序化匹配评估，显式处理空字段、无效候选、重复候选
- `report-runs`: 汇总成功 / failed / invalid_output / rerun recovered

## Directory

```text
code/
  analysis_setting_experiment/
  tests/
results/
  runs/
  evaluations/
```

## Usage

在仓库根目录下：

```bash
PYTHONPATH=code python -m analysis_setting_experiment.cli prepare-data \
  --benchmark-path data/review_level_analysis_setting_v1_title_enrichment_v3/review_level_analysis_setting_v1_title_enrichment_v3/benchmark.jsonl \
  --output-dir results/abstract_sr_direct_generation
```

```bash
PYTHONPATH=code python -m analysis_setting_experiment.cli run \
  --dataset-path results/abstract_sr_direct_generation/splits/dev.jsonl \
  --output-dir results/abstract_sr_direct_generation \
  --backend mock \
  --model-name gpt-5.4-mini \
  --model-version local \
  --split dev \
  --concurrency 8
```

```bash
PYTHONPATH=code python -m analysis_setting_experiment.cli evaluate \
  --dataset-path results/abstract_sr_direct_generation/splits/dev.jsonl \
  --output-dir results/abstract_sr_direct_generation \
  --model-name gpt-5.4-mini \
  --split dev
```

## Rerun / Resume

- 默认不会覆盖 `success`
- 每个 review 的 `state.json` 和 `latest_prediction.json` 会在任务完成后立刻落盘，支持断电恢复
- 整体运行进度会持续写入 `runs/<model>/<split>/progress.json`
- `--rerun-failed` 只重跑 `failed`
- `--rerun-invalid-output` 只重跑 `invalid_output`
- `--rerun-empty-output` 重跑解析成功但输出空列表的样本
- `--review-id REVIEW_ID` 可指定单个或多个 review 强制重跑

## Notes

- prompt 固定不要求输出 `analysis_label`
- `reported_outcome_measures` 只参与辅助字段分析，不进入主匹配权重
- 当前提供 `mock`、`json_file`、`openai` 三种 backend
- `openai` backend 优先读取仓库根目录下的 `analysis_setting.local.json`，其次读取 `--api-key` / `--base-url`，最后回退到 `OPENAI_API_KEY` / `OPENAI_BASE_URL` 环境变量
- 可参考仓库根目录的 `analysis_setting.local.example.json` 创建本地配置文件，支持 `api_key`、`base_url`、`model`
- 建议先用 `--review-id` 做单 review 联调，再扩到整个 split
- 默认模型名已切换为 `gpt-5.4-mini`
- 在 2026-05-19 的联调中，`https://api.zyai.online/v1` 对 `gpt-4.1-mini` 和 `gpt-4o-mini` 都返回了渠道不可用的 503；这类失败会被记录为 `failed` 并可后续 rerun

