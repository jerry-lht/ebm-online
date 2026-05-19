# Screening Experiments

本目录用于运行 `Q2CRBench-3` 和 `CSMeD-FT` screening 实验。

实验根目录：

```text
/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/experiments/screening-exp
```

默认 Python 环境：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python
```

## Current Methods

当前已实现并可运行的方法：

- `direct_criteria_aware`
  - CLI: `python -m screening.cli.run_direct_llm`
  - 主线已对齐 `CSMeD-FT abstract_only`
- `criterion_wise_evidence_grounded`
  - CLI: `python -m screening.cli.run_criterion_wise`
  - 当前 Phase 8 只服务 `CSMeD-FT`
  - 当前主线 prompt: `criterion_wise/v2`
  - 当前支持：
    - `full_text_only`
    - `abstract_plus_full_text`

## Data Preparation

准备 `CSMeD-FT` 标准化 examples：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.prepare_csmed_ft \
  --data-root data \
  --force
```

主要输出：

- `results/data/csmed_ft/*.examples.jsonl`
- `results/data/csmed_ft/manifest.csv`
- `results/data/csmed_ft/data_quality.json`
- `results/data/csmed_ft/data_quality.md`
- `results/tables/csmed_ft_dataset_summary.csv`

## Phase 8 Runner

`criterion_wise_evidence_grounded` 的设计目标是：

- 从 `criteria.inclusion` / `criteria.exclusion` 构建 review-clause-driven criterion set
- 对每个 criterion 做 deterministic keyword retrieval
- 让 LLM 只输出 `criterion_judgments`
- 在本地做 conservative aggregation，得到最终二分类 `decision`

当前 `CSMeD-FT` loader 已修复为真实 metadata 对齐的 prose-first criteria parsing：

- 优先从 `review_metadata["criteria"]` section prose 抽取 clauses
- 仅在结构化抽取为空或过少时补充 `criteria_text`
- 原始 clause source 保存到 `example.criteria.raw["parsed_review_clauses"]`

criterion planning 现在优先使用 `review_clauses`；只有 inclusion 和 exclusion 都为空时才退回 fallback：

- `question_match`
- `explicit_exclusion_signal`

重建后的真实 coverage（`2026-05-16`）：

- `train full_text_only`: `2010/2010` 非空 inclusion，`1930/2010` 非空 exclusion，`0` both empty
- `dev full_text_only`: `633/633` 非空 inclusion，`584/633` 非空 exclusion，`0` both empty
- `test full_text_only`: `615/620` 非空 inclusion，`604/620` 非空 exclusion，`5` both empty
- `test-small full_text_only`: `45/47` `review_clauses`，`2/47` `fallback_question_only`
- `test-small abstract_plus_full_text`: `45/47` `review_clauses`，`2/47` `fallback_question_only`

### Example Commands

`CSMeD-FT test-small full_text_only`:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.run_criterion_wise \
  --examples results/data/csmed_ft/test-small.full_text_only.examples.jsonl \
  --provider-config code/config/llm_providers.local.yaml \
  --provider openai-compatible \
  --model gpt-5.4-mini \
  --input-setting full_text_only \
  --prompt-version v3 \
  --run-id csmed_ft_test_small_fulltext_criterion_v3_gpt54mini_smoke3_20260516 \
  --limit 3
```

`CSMeD-FT test-small abstract_plus_full_text`:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m screening.cli.run_criterion_wise \
  --examples results/data/csmed_ft/test-small.abstract_plus_full_text.examples.jsonl \
  --provider-config code/config/llm_providers.local.yaml \
  --provider openai-compatible \
  --model gpt-5.4-mini \
  --input-setting abstract_plus_full_text \
  --prompt-version v3 \
  --run-id csmed_ft_test_small_absft_criterion_v3_gpt54mini_smoke3_20260516 \
  --limit 3
```

### Output Contract

Phase 8 prompt要求模型只返回：

```json
{
  "criterion_judgments": {
    "inc_1": {
      "text": "Adults with chronic kidney disease",
      "judgment": "yes | no | unclear"
    }
  }
}
```

写盘前由本地代码补全为兼容 `ScreeningPrediction` 的最终结构，包括：

- `decision`
- `criterion_judgments`
- `failed_criterion`
- `main_reason`
- `evidence_spans`

预测 metadata 会额外记录：

- `prediction_schema=criterion_wise_minimal_v1`
- `criterion_mode=raw_review_criteria_one_shot`
- `aggregation_status`
- `criteria_source`
- `input_setting`
- `text_source`

### Input And Aggregation

当前主线不再依赖 retrieval 作为 Phase 8 主路径。

运行时直接输入：

- `review question`
- `raw review criteria`
- `title`
- `abstract`
- `full text`

当前 aggregation policy 固定为 `conservative_binary_with_needs_review_flag`：

- 任一 exclusion criterion 为 `yes` -> `exclude`
- 任一 inclusion criterion 为 `no` -> `exclude`
- 否则只要有 `unclear` -> 顶层 `decision=include`，但 `aggregation_status=needs_review`
- 否则 -> `include_clear`

## Run Artifacts

`criterion_wise_evidence_grounded` 输出到：

- `results/preds/csmed_ft/<split>/criterion_wise_evidence_grounded/<run_id>/`
- `results/logs/csmed_ft/<split>/criterion_wise_evidence_grounded/<run_id>/`
- `results/metrics/csmed_ft/<split>/criterion_wise_evidence_grounded/<run_id>.json`

关键产物：

- `predictions.jsonl`
- `errors.jsonl`
- `evaluation_examples.jsonl`
- `run_metadata.json`

## Verification

当前已完成的本地验证：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python \
  -m pytest code/tests/test_csmed_ft_loader.py code/tests/test_criterion_wise.py -q
```

结果：`30 passed`

真实 smoke 已完成：

- `full_text_only --limit 1`: `1/1` success
- `full_text_only --limit 3`: `2 success / 1 provider_invalid_json`
- `abstract_plus_full_text --limit 1`: `1/1` success
- `abstract_plus_full_text --limit 3`: `3/3` success

如果多线程 smoke 里出现单个 provider 失败，先保留失败样本，再单独 rerun 该样本。

说明：`gpt-5.2` provider 已确认服务异常；当前本地配置已切换到 `gpt-5.4-mini`。
