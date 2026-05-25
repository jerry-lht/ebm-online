# Screening Experiment Implementation TODO

本文档用于指导后续按阶段实现 `code/experiment_design.md`。目标不是一次性跑完所有实验，而是先搭好可复现的数据、评估、运行和日志框架，再逐步接入 direct LLM baseline、criterion-wise evidence-grounded 方法、conservative two-stage pipeline 和 reason quality 评测。

## Current Repo Facts

- 实验根目录：`/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/experiments/screening-exp`
- 实验 Python 环境：`/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv`
- 实验设计文档：`code/experiment_design.md`
- 数据目录：
  - `data/Q2CRBench-3/`
  - `data/CSMeD-FT/`
- 结果目录：`results/`
- 当前代码状态：
  - 已建立 `screening` Python package、配置模板、统一 schema、I/O helper、基础 CLI、测试目录、dataset loaders、evaluation framework、direct LLM runner 和 criterion-wise runner。
  - Phase 8 的 CSMeD-FT `dev` prompt ablation 已完成，包含 direct decision baseline、raw criteria baseline、fixed criteria-list 对照和 hybrid fixed+raw 对照。
  - Q2CRBench-3 本地 screened records 只有 `2024 KDIGO CKD`；`2020 EAN Dementia` 和 `2021 ACR RA` screened records 因版权限制缺失，作为后续 blocker 显式记录。
  - CSMeD-FT 本地 split 为 `train/dev/test/sample`；`sample` 在 inventory 中按本地 `test-small` alias 报告。
  - 当前严禁继续用 `test` 做 prompt tuning；`test` 上已跑结果只作为冻结的 exploratory baseline，后续 prompt/aggregation/two-stage 选择必须在 `dev` 上完成。

## Implementation Principles

- 只使用公开 benchmark 数据；不把项目中其他本地 Cochrane 文件夹作为实验数据源。
- Q2CRBench-3 与 CSMeD-FT 可以有各自 loader，但必须转换到统一 example、prediction 和 metric schema。
- Stage 1 abstract screening 的首要目标是高 sensitivity；不确定样本不能被自动排除。
- `needs_review`、`include_for_review` 和 Stage 1 的 `unclear` 在安全评估中统一按 include/pass 处理。
- LLM 输出必须保存 raw response、parsed JSON、validation errors 和最终 normalized prediction。
- 每次运行必须记录 config、prompt version、model/provider、输入数据版本、运行时间、命令和输出路径。
- 主实验必须运行实际 LLM 调用并保存真实模型输出；mock/offline runner 只允许用于单元测试、CLI smoke test 和 parser 验证，不能作为实验结果。
- 数据划分优先使用 benchmark 官方/原始发布的 split；只有当本地数据没有官方 split 或 split 不可恢复时，才允许生成自定义 split，并必须在 run metadata 和报告中明确标记。
- 外部 API 数据构建、大规模 LLM 调用、embedding retrieval 优化和人工评测应作为独立阶段执行，不混入基础框架阶段。
- 所有结果表必须能通过 run index 追溯到输入 examples、prompt/schema 版本、prediction 文件和 metric 文件。
- 当前优先级是评估 LLM screening 效果；reason support、hallucination 和人工复核样本作为辅助分析，不阻塞主结果表生成。

## Experiment Directory Layout

本实验位于：

```text
/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/experiments/screening-exp
```

建议在 `code/` 目录下新增 Python package：

```text
screening-exp/
  code/
    experiment_design.md
    Screening-Implementation-TODO.md
    config/
      llm_providers.example.yaml
      experiment_defaults.yaml
    screening/
      __init__.py
      schemas.py
      paths.py
      config.py
      io_utils.py
      datasets/
        __init__.py
        inventory.py
        q2crbench.py
        csmed_ft.py
      prompts/
        __init__.py
        direct.py
        criterion_wise.py
      retrieval/
        __init__.py
        evidence_pool.py
        keyword.py
      evaluation/
        __init__.py
        decision.py
        reasons.py
        tables.py
      pipeline/
        __init__.py
        aggregation.py
        two_stage.py
      cli/
        __init__.py
        inventory_data.py
        prepare_q2crbench.py
        prepare_csmed_ft.py
        evaluate_predictions.py
        run_direct_llm.py
        run_criterion_wise.py
        run_two_stage.py
        build_tables.py
    tests/
  data/
    Q2CRBench-3/
    CSMeD-FT/
  results/
```

默认所有命令从 `screening-exp/` 实验根目录执行，并使用：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.inventory_data --help
```

不要把 `code/` 当作 Python 包名；`code/` 只是实验代码目录，通过 `PYTHONPATH=code` 加入模块搜索路径。

## Data And Result Organization Rules

统一结果目录约定：

- `results/data/`: 保存标准化 examples、dataset summaries、dataset manifests 和数据质量检查结果。
- `results/preds/`: 保存各方法预测，按 benchmark、split、method、setting 和 timestamp 分目录。
- `results/metrics/`: 保存 evaluator 原始 JSON 指标，包括 confusion counts、safety metrics 和 reason metrics。
- `results/tables/`: 保存统一对比表，优先同时输出 `.csv` 和 `.md`。
- `results/logs/`: 保存 run metadata、命令、config、prompt/schema version、model/provider 和运行时间。
- `results/reports/`: 保存错误分析样本、人评样本、高风险 false negative 和 unsupported reason case。

建议统一表格：

- `results/tables/dataset_inventory.csv`: benchmark/split 级别数据完整性摘要。
- `results/tables/document_manifest.csv`: example 级别索引，包含 benchmark、split、review_id、study_id、label、has_abstract、has_full_text。
- `results/tables/q2crbench_abstract_screening.csv`: Q2CRBench-3 abstract screening 主结果。
- `results/tables/q2crbench_evidence_profile_screening.csv`: Q2CRBench-3 evidence-profile 辅助 setting 结果；不得称为 full-text 主结果。
- `results/tables/csmed_ft_final_screening.csv`: CSMeD-FT final screening 主结果。
- `results/tables/one_step_vs_two_stage.csv`: one-step 与 two-stage 对比表。
- `results/tables/reason_quality.csv`: reason accuracy、support rate 和 hallucination 风险表。
- `results/tables/run_index.csv`: 每次运行的 method、setting、config path、prediction path、metric path、timestamp。
- `results/tables/automation_readiness.csv`: 按实验和方法汇总是否达到设计中的 sensitivity、balanced accuracy、high-confidence FN 和 unsupported reason 阈值。

每个方法的预测和指标都必须能通过 `run_index.csv` 找回对应输入、配置和输出。

## Progress Tracker

后续每次让 Codex 执行时，先要求它读取并更新本节。状态只使用以下枚举：

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done
- `[!]` Blocked

| Phase | Status | Last Updated | Output / Notes |
|---|---|---|---|
| Phase 1: Project Skeleton | `[x]` | 2026-05-14 | Created `code/screening/` scaffold, config templates, Phase 1 tests, and validated imports/CLI help/pytest smoke commands. |
| Phase 2: Unified Schemas And I/O | `[x]` | 2026-05-14 | Added shared Pydantic schemas, JSON/JSONL helpers, prediction response normalization, and Phase 2 tests; `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q` passed. |
| Phase 3: Dataset Inventory And Validation | `[x]` | 2026-05-14 | Added local read-only Q2CRBench-3 and CSMeD-FT inventory scanner, real `inventory_data` CLI, artifact writers, toy fixture tests, and generated inventory/blocker artifacts. Blockers recorded: missing Q2CRBench screened records for `2020 EAN Dementia` and `2021 ACR RA`; CSMeD-FT `sample` reported as `test-small`. |
| Phase 4: Q2CRBench-3 Data Loader | `[x]` | 2026-05-14 | Added `code/screening/datasets/q2crbench.py`, `code/screening/cli/prepare_q2crbench.py`, evidence-profile input setting support, and Q2CRBench loader tests. Generated KDIGO artifacts: `results/data/q2crbench/kdigo_ckd.abstract_only.examples.jsonl` (16,312 examples), `results/data/q2crbench/kdigo_ckd.evidence_profile.examples.jsonl` (13,145 examples), manifest, data quality JSON/MD, and summary CSV. EAN/ACR screened-record blockers remain recorded. |
| Phase 5: CSMeD-FT Data Loader | `[x]` | 2026-05-14 | Added `code/screening/datasets/csmed_ft.py`, `code/screening/cli/prepare_csmed_ft.py`, and `code/tests/test_csmed_ft_loader.py`; generated `results/data/csmed_ft/*.examples.jsonl`, `manifest.csv`, `data_quality.json`, `data_quality.md`, and `results/tables/csmed_ft_dataset_summary.csv`. Verified official split counts match the local baseline exactly; `sample` is exported only as `test-small`. Additional data-quality note: 68 records have neither title nor abstract, so `abstract_only` counts are lower than total document counts by design. |
| Phase 6: Evaluation Framework | `[x]` | 2026-05-15 | Added `code/screening/evaluation/decision.py`, `code/screening/evaluation/tables.py`, and a real `code/screening/cli/evaluate_predictions.py`; implemented decision/safety/workload/readiness metrics, readiness-table reconstruction from metrics JSON, and Phase 6 tests. Verified commands: `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_evaluation_decision.py code/tests/test_cli_help.py code/tests/test_config.py -q` and `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_schemas.py code/tests/test_io_utils.py -q` passed. Current limitation kept explicit by design: unsupported-exclusion and hallucinated-reason metrics remain `not_evaluated` placeholders until Phase 10. |
| Phase 7: Direct Criteria-aware LLM Baseline | `[~]` | 2026-05-16 | Reframed the abstract-only mainline into a benchmark-aligned minimal-output baseline: added `code/screening/prompts/direct/v3.txt` plus setting-aware prompt registry support in `code/screening/prompts/direct.py`, introduced `AbstractScreeningPrediction` for `abstract_only` runs, and routed `run_direct_llm`/`evaluate_predictions` through schema-aware parsing so abstract-only outputs now require only `decision` and `main_reason` while full-text settings keep the richer schema. Targeted Phase 7 tests pass, and real `CSMeD-FT abstract_only` runs now exist for `test-small` and `test`; current `v3` recall is about `82%` on `test`, with Stage 1 readiness still failing and `v2` remaining slightly stronger on FN/recall. |
| Phase 8: Criterion-wise Evidence-grounded Method | `[x]` | 2026-05-16 | CSMeD-FT `dev` ablation batch completed with zero remaining provider errors after targeted retries. Direct decision `abstract_plus_full_text` is the high-sensitivity baseline: sensitivity 0.9137 / specificity 0.3427 / balanced accuracy 0.6282 / macro F1 0.5210. Raw criteria is the strongest one-step balanced arm: 0.6142 / 0.8415 / 0.7279 / 0.7303. Fixed specs and hybrid specs+raw are negative ablations: they over-exclude and collapse recall. Frozen exploratory `test` run remains diagnostic only and must not be used for tuning. Results: `results/tables/csmed_ft_dev_prompt_ablation.csv`, `results/reports/csmed_ft_dev_prompt_ablation/summary.md`. |
| Phase 9: Conservative Two-stage Pipeline | `[x]` | 2026-05-16 | Implemented `code/screening/pipeline/two_stage.py`, `code/screening/cli/run_two_stage.py`, and `code/tests/test_two_stage.py`; ran the missing real Stage 1 `CSMeD-FT dev.abstract_only` direct v3 batch with 632/632 successes, then composed two dev two-stage runs against existing Phase 8 Stage 2 predictions. Final comparison: both two-stage policies reduce full-text workload by 40.26% (374/626 sent to Stage 2, 0 missing Stage 2 predictions). Direct two-stage: sensitivity 0.8274 / specificity 0.5501 / balanced accuracy 0.6888 / macro F1 0.6324. Criteria raw v3 two-stage: sensitivity 0.5635 / specificity 0.8998 / balanced accuracy 0.7316 / macro F1 0.7447. Neither passes readiness because sensitivity drops versus one-step references and false negatives remain. Outputs: `results/tables/one_step_vs_two_stage.csv`, `results/reports/csmed_ft_two_stage_dev/summary.md`, `results/preds/csmed_ft/dev/two_stage/*`, `results/metrics/csmed_ft/dev/two_stage/*.json`. Tests: targeted Phase 9 suite and full `code/tests` pass. |
| Phase 10: Reason Quality Evaluation | `[ ]` | - | - |
| Phase 11: Reporting And Error Analysis | `[ ]` | - | - |

每个 Phase 完成后，Codex 应同时更新：

- 对应 Phase 的 `Status / Last Updated / Output / Notes`
- 本文档中该 Phase 的 `Progress` 小节
- 产生或修改的关键文件路径
- 生成的结果文件路径
- 已执行的测试或验证命令
- 若有 blocker，使用 `[!]` 并写明下一步需要用户提供什么

## Phase 1: Project Skeleton

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Created `code/screening/` package scaffold with `paths.py`, `config.py`, and placeholder CLIs for `inventory_data`, `evaluate_predictions`, and `run_direct_llm`; added `code/config/llm_providers.example.yaml` and `code/config/experiment_defaults.yaml`; added `code/tests/` with path, config, and CLI smoke coverage; validation commands: `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -c "import screening; import screening.paths; import screening.config"`, `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.inventory_data --help`, `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.evaluate_predictions --help`, `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.run_direct_llm --help`, `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q`.

### Goal

建立实验代码骨架、配置模板、基础 CLI 和测试目录，使后续阶段可以在统一 package 内继续开发。

### Tasks

- 新建 `code/screening` Python package。
- 新建 `code/screening/cli`、`datasets`、`evaluation`、`pipeline`、`prompts`、`retrieval` 子模块。
- 新增基础 CLI 入口，至少包含 `--help` 可运行的 scaffold：
  - `inventory_data`
  - `evaluate_predictions`
  - `run_direct_llm`
- 新增配置模板：
  - `code/config/llm_providers.example.yaml`
  - `code/config/experiment_defaults.yaml`
- 新增 `code/tests/` 测试目录。

### Expected Outputs

- `code/screening/__init__.py`
- `code/screening/paths.py`
- `code/screening/config.py`
- `code/screening/cli/*.py`
- `code/config/llm_providers.example.yaml`
- `code/config/experiment_defaults.yaml`

### Acceptance Criteria

- 从实验根目录可 import `screening`。
- 基础 CLI 的 `--help` 可运行。
- provider 配置模板不包含真实 API key。
- 不要求本阶段读取真实 benchmark 数据。

## Phase 2: Unified Schemas And I/O

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Added `code/screening/schemas.py` with unified example, prediction, criterion judgment, evidence span, and run metadata schemas; added `code/screening/io_utils.py` with UTF-8 JSON/JSONL helpers, Pydantic model JSONL round trip support, raw response parsing, validation error formatting, and prediction normalization; added `code/tests/test_schemas.py` and `code/tests/test_io_utils.py`; validation command: `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q` passed with 29 tests.

### Goal

定义 Q2CRBench-3、CSMeD-FT、LLM prediction 和 evaluation 共用的数据结构，避免不同阶段输出不兼容。

### Tasks

- 定义标准 example schema：
  - benchmark、split、review_id、study_id
  - question、PICO/PICOS、inclusion criteria、exclusion criteria
  - title、abstract、full-text sections、evidence profile
  - gold decision、gold reason、metadata
- 定义 prediction schema：
  - decision: `include | exclude | needs_review`
  - confidence
  - criterion-level judgments
  - failed criterion
  - main reason
  - evidence spans
  - raw response metadata
- 定义 run metadata schema。
- 实现 JSON/JSONL read/write helper。
- 实现 prediction validation 与 normalization 的基础函数。

### Expected Outputs

- `code/screening/schemas.py`
- `code/screening/io_utils.py`
- schema 和 I/O 单元测试。

### Acceptance Criteria

- Toy examples 和 predictions 可以 JSONL round trip。
- prediction validation 能识别非法 decision、缺失字段和非 JSON response。
- schema 支持 abstract-only、full-text-only、abstract + full-text 三类输入设置。

## Phase 3: Dataset Inventory And Validation

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Implemented `code/screening/datasets/inventory.py` with read-only scanners for Q2CRBench-3 parquet configs and CSMeD-FT CSV/metadata files; replaced the Phase 1 placeholder `code/screening/cli/inventory_data.py` with a real CLI supporting `--dataset {all,q2crbench,csmed_ft}`, `--data-root`, and `--output-dir`; added `code/tests/test_inventory.py`; generated `results/data/dataset_inventory.json`, `results/tables/dataset_inventory.csv`, `results/tables/document_manifest.csv`, and `results/reports/data_blockers.md`. Real local inventory output: 7 dataset rows, 19,704 document manifest rows, 2 Q2CRBench blockers. Validation commands run: `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_inventory.py -q`, `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q`, and `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.inventory_data --dataset all`.

### Goal

在正式转换数据前，确认本地 Q2CRBench-3 与 CSMeD-FT 的文件、split、label 和全文可用性，明确哪些数据可进入主实验，哪些需要补充。

### Tasks

- 扫描 `data/Q2CRBench-3/` 和 `data/CSMeD-FT/`。
- 识别可用 split、review/question 数、candidate study 数、include/exclude label 数。
- 检查每条记录是否包含 title、abstract、full text/XML/evidence profile。
- 输出缺失 label、缺失 abstract、缺失 full text、无法解析文件的清单。
- 对 Q2CRBench-3，单独标记因版权限制可能不完整的 review/question。
- 对 CSMeD-FT，单独标记需要外部 API/GROBID/cookie 才能构建的缺失全文。

### Expected Outputs

- `code/screening/datasets/inventory.py`
- `code/screening/cli/inventory_data.py`
- `results/data/dataset_inventory.json`
- `results/tables/dataset_inventory.csv`
- `results/tables/document_manifest.csv`
- `results/reports/data_blockers.md`

### Acceptance Criteria

- 不调用外部 API。
- 不假设数据完整；所有缺失项进入 blocker/report。
- 后续 loader 可以基于 inventory 结果决定哪些 split/review 可进入主实验。
- Q2CRBench-3 缺失的 EAN/ACR screened records 已作为 dataset-level blockers 报告，不被静默忽略。
- CSMeD-FT `sample` 已显式按本地 `test-small` alias 报告，空 `main_text` 行保留在 manifest 中并标记为 full text unavailable。

## Phase 4: Q2CRBench-3 Data Loader

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Implemented `code/screening/datasets/q2crbench.py` and `code/screening/cli/prepare_q2crbench.py`; added `code/tests/test_q2crbench_loader.py` plus CLI/schema coverage for the `evidence_profile` setting. The loader reads local Q2CRBench parquet configs, converts only `2024 KDIGO CKD` screened records into main examples, maps `PICO_IDX` to `Clinical_Questions.Index`, preserves source split/review metadata, normalizes `Included`/`Excluded` labels, excludes records with missing title+abstract from abstract-only examples, and writes data quality findings for missing text, labels, clinical questions, JSON parse issues, missing evidence profiles, and dataset-level EAN/ACR blockers. Generated artifacts: `results/data/q2crbench/kdigo_ckd.abstract_only.examples.jsonl` (16,312 examples), `results/data/q2crbench/kdigo_ckd.evidence_profile.examples.jsonl` (13,145 auxiliary evidence-profile examples, not full text), `results/data/q2crbench/manifest.csv`, `results/data/q2crbench/data_quality.json`, `results/tables/q2crbench_dataset_summary.csv`, and `results/reports/q2crbench_data_quality.md`. Validation commands run: `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_q2crbench_loader.py -q`, `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q`, and `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.prepare_q2crbench --force`.

### Goal

将 Q2CRBench-3 中可用的 question、PICO/PICOS、candidate records、evidence profile 和 gold labels 转换为统一 screening examples。当前本地 Q2CRBench-3 没有真实 full text；Phase 4 不生成 full-text 主数据。

### Tasks

- 读取 Q2CRBench-3 本地数据结构。
- 抽取 review/clinical question、PICO/PICOS、study design requirement 和 criteria。
- 抽取 candidate title/abstract。
- 抽取可用 evidence profile；不伪装为 full text 或 XML sections。
- 标准化 gold decision 为 `include | exclude`。
- 写出 abstract screening 主 examples 和 evidence-profile 辅助 setting examples。
- 生成 manifest 和 split/review 级统计。
- 保留并输出 Q2CRBench-3 原始/官方数据划分或 review/question 分组；不要为了方便混合不同 review/question 后随机切分。

### Expected Outputs

- `code/screening/datasets/q2crbench.py`
- `code/screening/cli/prepare_q2crbench.py`
- `results/data/q2crbench/*.examples.jsonl`
- `results/data/q2crbench/manifest.csv`
- `results/tables/q2crbench_dataset_summary.csv`

### Acceptance Criteria

- 每条 example 都有稳定 `review_id` 和 `study_id`。
- examples 中记录 `source_split`、`source_review` 或等价字段，确保评估可以按官方/原始 split 或 review/question 分组复现。
- 缺少 gold label 的记录不进入主评估 examples，但保留在 data quality report。
- evidence-profile 缺失不影响 abstract-only examples 生成；Q2CRBench evidence-profile examples 不得在后续报告中称为 full-text examples。

## Phase 5: CSMeD-FT Data Loader

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Implemented `code/screening/datasets/csmed_ft.py` with split alias normalization (`sample -> test-small`), review metadata join, `ScreeningExample` conversion, setting-aware filtering for `abstract_only` / `full_text_only` / `abstract_plus_full_text`, manifest rows with per-setting exclusion reasons, baseline-count verification, and data quality reports. Added `code/screening/cli/prepare_csmed_ft.py` and `code/tests/test_csmed_ft_loader.py`. Generated real artifacts: `results/data/csmed_ft/train.abstract_only.examples.jsonl` (2008), `train.full_text_only.examples.jsonl` (2010), `train.abstract_plus_full_text.examples.jsonl` (1982), `dev.abstract_only.examples.jsonl` (632), `dev.full_text_only.examples.jsonl` (633), `dev.abstract_plus_full_text.examples.jsonl` (626), `test.abstract_only.examples.jsonl` (627), `test.full_text_only.examples.jsonl` (620), `test.abstract_plus_full_text.examples.jsonl` (614), `test-small.abstract_only.examples.jsonl` (48), `test-small.full_text_only.examples.jsonl` (47), `test-small.abstract_plus_full_text.examples.jsonl` (47), plus `results/data/csmed_ft/manifest.csv`, `results/data/csmed_ft/data_quality.json`, `results/data/csmed_ft/data_quality.md`, and `results/tables/csmed_ft_dataset_summary.csv`. Validation commands run: `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.prepare_csmed_ft --help`, `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_csmed_ft_loader.py -q`, and `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m screening.cli.prepare_csmed_ft --force`. Verified split-level baseline counts match the expected local facts exactly: `train` 2053 docs / 148 reviews / 904 include / 1149 exclude / 43 blank `main_text`, `dev` 644 / 36 / 202 / 442 / 11, `test` 636 / 29 / 278 / 358 / 16, `test-small` 50 / 16 / 22 / 28 / 3. Data quality reports recorded no invalid labels, no missing review metadata, and no baseline mismatches; 68 records lack both title and abstract, so they are retained in the manifest but excluded from `abstract_only` and `abstract_plus_full_text` settings by design.

### Goal

将 CSMeD-FT train/dev/test/test-small 转换为统一 screening examples，用于 full-text final screening 泛化验证。

### Tasks

- 读取 CSMeD-FT 本地 split。
- 抽取 review metadata、criteria、title、abstract、full text/XML 和 gold labels。
- 标准化 final decision 与 gold reason。
- 生成 train/dev/test/test-small examples。
- 严格保留 CSMeD-FT 官方 train/dev/test/test-small split；`test-small` 默认用于 smoke test 和小规模真实 LLM 试跑，`test` 用于主结果。
- 输出全文可用性和文本长度统计。

### Expected Outputs

- `code/screening/datasets/csmed_ft.py`
- `code/screening/cli/prepare_csmed_ft.py`
- `results/data/csmed_ft/*.examples.jsonl`
- `results/data/csmed_ft/manifest.csv`
- `results/tables/csmed_ft_dataset_summary.csv`

### Acceptance Criteria

- 所有 split 的 doc count、include count、exclude count 可复查。
- 输出的 split 名称必须与官方 split 对齐；若本地数据缺少某个官方 split，必须在 blocker/report 中说明。
- 无 full text 的样本不进入 full-text 主评估，除非明确标记为 abstract-only setting。
- 不在本阶段调用 Semantic Scholar、CORE、GROBID 或 Cochrane Library。

## Phase 6: Evaluation Framework

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-15  
**Notes:** Implemented `code/screening/evaluation/decision.py` and `code/screening/evaluation/tables.py` as the shared Phase 6 evaluator surface; replaced the placeholder `code/screening/cli/evaluate_predictions.py` with a real CLI that reads `ScreeningPrediction` / `ScreeningExample` JSONL, computes decision/safety/workload/readiness metrics, writes metrics JSON, and reconstructs `results/tables/automation_readiness.csv` from metrics JSON rows. Added `code/tests/test_evaluation_decision.py` to cover toy confusion matrices, `needs_review` handling, threshold overrides, readiness profiles, table upsert behavior, and CLI end-to-end evaluation. Updated `code/config/experiment_defaults.yaml` and `code/tests/test_config.py` so the default high-confidence FN threshold is `0.8`, matching the design doc and this phase’s acceptance criteria. Validation commands run: `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_evaluation_decision.py code/tests/test_cli_help.py code/tests/test_config.py -q` and `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_schemas.py code/tests/test_io_utils.py -q`. Phase boundary note: `unsupported_exclusion_*` and `hallucinated_reason_*` are intentionally emitted as `null` with `placeholder_status=not_evaluated`; Phase 10 will replace these placeholders with real reason-quality evaluation.

### Goal

实现 decision、safety、workload 和基础 reason 指标，使后续所有方法使用同一个 evaluator。

### Tasks

- 实现 decision metrics：
  - sensitivity/recall for included studies
  - specificity
  - precision
  - balanced accuracy
  - macro F1
  - false negative count
- 实现 safety metrics：
  - high-confidence false negative
  - unsupported exclusion placeholder
  - hallucinated reason placeholder
- 实现 workload metrics：
  - full-text workload
  - full-text workload reduction
- 约定 `needs_review` 在安全评估中计为 include。
- 输出 evaluator JSON 和可汇总 row。
- 生成 automation readiness summary，至少覆盖：
  - Stage 1: sensitivity >= 0.98 and high-confidence FN = 0
  - Full-text: sensitivity >= 0.95, balanced accuracy >= 0.80, high-confidence FN = 0
  - Two-stage: end-to-end sensitivity close to full-text one-step, workload lower than full-text one-step, high-confidence FN = 0

### Expected Outputs

- `code/screening/evaluation/decision.py`
- `code/screening/evaluation/tables.py`
- `code/screening/cli/evaluate_predictions.py`
- `code/tests/test_evaluation_decision.py`
- `results/tables/automation_readiness.csv`

### Acceptance Criteria

- Toy confusion matrix 测试覆盖 include/exclude/needs_review。
- high-confidence FN threshold 默认 `0.8`，可由 config 覆盖。
- evaluator 不依赖具体 LLM provider。
- automation readiness 结果必须能从 metrics JSON 重建，不能只存在于手写报告中。

## Phase 7: Direct LLM Baseline

**Progress:** `[~]` In progress  
**Last Updated:** 2026-05-16  
**Notes:** Phase 7 abstract-only mainline is now explicitly a benchmark-aligned minimal-output baseline. Added `code/screening/prompts/direct/v3.txt` and extended `code/screening/prompts/direct.py` so `v3` is abstract-only only, rewrites the task framing around `review question + title + abstract`, and asks for only `decision` plus `main_reason`. Added `AbstractScreeningPrediction` in `code/screening/schemas.py`, generalized response parsing/loading in `code/screening/io_utils.py`, and updated `code/screening/cli/run_direct_llm.py` plus `code/screening/cli/evaluate_predictions.py` so abstract-only `v3` runs use the minimal schema while full-text and legacy versions keep the richer schema. Updated Phase 7 tests in `code/tests/test_schemas.py`, `code/tests/test_io_utils.py`, `code/tests/test_direct_prompt.py`, `code/tests/test_evaluation_decision.py`, and `code/tests/test_run_direct_llm.py`; validation command `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_schemas.py code/tests/test_io_utils.py code/tests/test_direct_prompt.py code/tests/test_evaluation_decision.py code/tests/test_run_direct_llm.py -q` passes (`51 passed`).

Real-run status is now established rather than pending:

- `CSMeD-FT test-small abstract_only v3` smoke run completed: `results/metrics/csmed_ft/test-small/direct_criteria_aware/csmed_ft_test_small_abs_v3_smoke20.json`
- `CSMeD-FT test abstract_only v3` full run completed: `results/metrics/csmed_ft/test/direct_criteria_aware/csmed_ft_test_abs_v3_full.json`
- `CSMeD-FT test abstract_only v3` rerun completed: `results/metrics/csmed_ft/test/direct_criteria_aware/csmed_ft_test_abs_v3_full_rerun_20260516.json`

Current outcome on the latest `v3` full rerun is still below Stage 1 safety/readiness expectations:

- evaluated examples: `621 / 627` (`6` provider-invalid-json empty responses were recorded in `errors.jsonl`)
- `TP=223`, `FN=47`, `FP=238`, `TN=113`
- `sensitivity=0.8259`, `specificity=0.3219`, `precision=0.4837`, `balanced_accuracy=0.5739`
- readiness remains failed because the current profile checks require `sensitivity >= 0.98` and `false_negative_count == 0`

Prompt-side conclusion at the moment:

- `v3` is the cleaner EBM-style abstract-screening formulation and remains the semantic mainline for `abstract_only`
- `v3` has not improved recall/FN versus the prior conservative `v2` full run
- current `v2` full-run reference remains slightly better on `test` (`sensitivity=0.8431`, `FN=43`) than the latest `v3` rerun (`sensitivity=0.8259`, `FN=47`)
- the remaining blocker is experimental quality for Stage 1 use, not schema/prompt plumbing

### Goal

实现 strong baseline：按 benchmark 当前真实提供的输入字段直接调用 LLM。当前主线 `CSMeD-FT abstract_only` 采用最小输出 contract，只要求 `decision` 和 `main_reason`；full-text 相关设置仍保留 richer schema。

### Tasks

- 实现 direct prompt builder。
- 支持三类 input setting：
  - abstract-only
  - full-text-only
  - abstract + full-text
- 当前 Phase 7 的 direct baseline 为全自动二分类：
  - `include`
  - `exclude`
- 当前主实验先严格对齐 benchmark：
  - `CSMeD-FT abstract_only` 当前按 `review question + title + abstract -> include/exclude` 运行
  - 不假设额外结构化 PICO 或 inclusion/exclusion criteria 已可用
- `abstract_only` 的最小输出 contract 只保留：
  - `decision`
  - `main_reason`
- full-text / richer setting 继续保留 criterion-level 输出。
- 不再使用 `needs_review` 或 self-reported `confidence` 作为主实验输出。
- 实现 provider config 读取，但真实 key 由用户本地填写。
- 保存 raw response、parsed prediction、validation errors 和 run metadata。
- 支持小样本 dry run，避免默认全量调用外部 API。
- 支持真实 LLM 调用，至少包括：
  - `--limit` 小样本真实调用
  - `--resume` 跳过已有 prediction
  - 失败请求记录 error，不静默丢样本
  - run metadata 记录 provider、model、temperature、max tokens、prompt version、开始/结束时间和样本数
- mock/offline provider 只能用于测试，不能写入主实验结果表。

### Expected Outputs

- `code/screening/prompts/direct.py`
- `code/screening/cli/run_direct_llm.py`
- `results/preds/*/direct_criteria_aware/*`
- `results/logs/*`

### Acceptance Criteria

- 可以对小样本 examples 运行并生成结构化 prediction JSONL。
- 非法 JSON 或 schema 不合格输出会被记录，不会静默丢失。
- prompt version 写入 run metadata。
- prompt 内容必须与 benchmark 当前真实字段对齐，不能假设未提供的结构化 criteria/PICO。
- evaluator 以二分类 decision 为主，Stage 1 readiness 关注 `sensitivity` 与 `false_negative_count`。
- 至少完成 `test-small` 或用户指定小样本的真实 LLM run，才能把该方法标记为实验可评估。
- 在成本允许时，需完成目标 benchmark 的正式真实 LLM run，并产出可用于主结果表的 prediction 和 metrics。

## Phase 8: Criterion-wise Evidence-grounded Method

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-16  
**Notes:** Current raw criterion-wise `test` run is frozen as an exploratory baseline, not a tuning set: `csmed_ft_test_absft_criterion_v3_gpt54mini_full_completed_20260516` completed 614/614 with sensitivity 0.6704, specificity 0.8473, and balanced accuracy 0.7588. Follow-up tuning is dev-only. Added prompt-only criteria modes to `code/screening/prompts/criterion_wise.py` and `code/screening/cli/run_criterion_wise.py`: `raw`, `fixed_specs`, and `hybrid_specs_raw`. Fixed/hybrid modes render stable `CriterionSpec` IDs from `build_csmed_criterion_specs()` and reject missing or unexpected returned IDs. New prompt assets: `code/screening/prompts/criterion_wise/fixed_specs_v1.txt` and `code/screening/prompts/criterion_wise/hybrid_specs_raw_v1.txt`. Full `dev` ablation is complete and documented in `results/tables/csmed_ft_dev_prompt_ablation.csv` plus `results/reports/csmed_ft_dev_prompt_ablation/summary.md`: direct decision `abstract_plus_full_text` gives sensitivity 0.9137 / specificity 0.3427 / balanced accuracy 0.6282 / macro F1 0.5210; raw criteria gives 0.6142 / 0.8415 / 0.7279 / 0.7303; fixed specs gives 0.1066 / 0.9720 / 0.5393 / 0.4993; hybrid specs+raw gives 0.0761 / 0.9837 / 0.5299 / 0.4770. Direct decision is now the required high-sensitivity baseline. Raw criteria is the current best one-step balanced baseline. Fixed/hybrid are negative ablations as currently prompted because they over-exclude and collapse recall.

### Goal

实现主方法和 dev-only prompt ablation：直接基于 raw review criteria prose + candidate title/abstract/full text 做 one-shot criterion judgments，并新增 fixed/hybrid `CriterionSpec` 对照，由本地保守聚合为 final decision。当前主线只覆盖 `CSMeD-FT`，不包含 `Q2CRBench`。

### Tasks

- 优先从 `criteria.raw["criteria"]` 渲染 raw review criteria prose。
- 无 `criteria` 时回退到 `criteria.raw["criteria_text"]`。
- 实现 one-shot criterion-wise prompt 和最小 schema validation。
- 实现 `--criteria-mode {raw,fixed_specs,hybrid_specs_raw}`，默认 `raw` 保持兼容。
- fixed/hybrid 模式必须校验模型返回的 criterion IDs 与固定 specs 一致。
- 允许模型只输出 `criterion_judgments`，由本地代码补全最终 `ScreeningPrediction`。
- 实现 conservative aggregation：
  - `exc=yes -> exclude`
  - `inc=no -> exclude`
  - `unclear -> include + aggregation_status=needs_review`
  - otherwise `include_clear`
- 写出带 aggregation metadata 的 run artifacts。
- 完成 smoke-first 真实验证。

### Expected Outputs

- `code/screening/retrieval/evidence_pool.py`
- `code/screening/retrieval/keyword.py`
- `code/screening/prompts/criterion_wise.py`
- `code/screening/prompts/criterion_wise/v1.txt`
- `code/screening/prompts/criterion_wise/fixed_specs_v1.txt`
- `code/screening/prompts/criterion_wise/hybrid_specs_raw_v1.txt`
- `code/screening/pipeline/criteria.py`
- `code/screening/pipeline/aggregation.py`
- `code/screening/cli/run_criterion_wise.py`
- `code/tests/test_criterion_wise.py`
- `results/preds/*/criterion_wise_evidence_grounded/*`
- `results/logs/*/criterion_wise_evidence_grounded/*`

### Acceptance Criteria

- 模型原始输出只需要最小 `criterion_judgments` JSON。
- fixed/hybrid mode 中缺失或额外 criterion ID 会写入 error record，不会静默进入 metrics。
- criterion-only 模型输出可以被本地补全为兼容现有 reader/evaluator 的最终 `ScreeningPrediction`。
- `run_metadata.json` 和 prediction metadata 包含 raw-criteria / aggregation 审计字段。
- 当关键 criterion 为 `unclear` 时，顶层 `decision` 保守记为 `include`，并在 metadata 中记录 `aggregation_status=needs_review`，而不是自动 exclude。
- 可以与 Phase 6 evaluator 对接。
- 已完成 `CSMeD-FT test-small full_text_only` 与 `abstract_plus_full_text` 的真实 smoke。

## Phase 9: Conservative Two-stage Pipeline

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-16  
**Notes:** Implemented the conservative two-stage policy and CLI, added focused tests, ran the missing real Stage 1 `CSMeD-FT dev.abstract_only` direct v3 batch, and composed two dev pipelines from existing Phase 8 Stage 2 predictions. The evaluation cohort is the 626-example `dev.abstract_plus_full_text` set to keep one-step and two-stage comparisons aligned; the 632-example abstract-only Stage 1 file is used only as the gate source. Stage 1 sent 374/626 examples to Stage 2 and auto-excluded 252/626. Both two-stage runs had 0 missing Stage 2 predictions and 40.26% workload reduction. Direct two-stage improved specificity and macro F1 over one-step direct but reduced sensitivity from 0.9137 to 0.8274. Criteria raw v3 two-stage improved specificity and macro F1 over one-step raw criteria but reduced sensitivity from 0.6142 to 0.5635. Current readiness remains false for both because false negatives remain and sensitivity gaps exceed the configured two-stage threshold.

### Completed Outputs

- Code:
  - `code/screening/pipeline/two_stage.py`
  - `code/screening/cli/run_two_stage.py`
  - `code/tests/test_two_stage.py`
- Stage 1 real dev run:
  - `results/preds/csmed_ft/dev/direct_criteria_aware/csmed_ft_dev_abstract_direct_v3_gpt54mini_full_20260516/predictions.jsonl`
  - `results/metrics/csmed_ft/dev/direct_criteria_aware/csmed_ft_dev_abstract_direct_v3_gpt54mini_full_20260516.json`
- Two-stage dev runs:
  - `results/preds/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_direct_v2_gpt54mini_20260516/`
  - `results/metrics/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_direct_v2_gpt54mini_20260516.json`
  - `results/preds/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_criteria_raw_v3_gpt54mini_20260516/`
  - `results/metrics/csmed_ft/dev/two_stage/csmed_ft_dev_two_stage_abstract_direct_v3_to_absft_criteria_raw_v3_gpt54mini_20260516.json`
- Tables and report:
  - `results/tables/one_step_vs_two_stage.csv`
  - `results/reports/csmed_ft_two_stage_dev/summary.md`

### Validation Commands

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_two_stage.py code/tests/test_evaluation_decision.py code/tests/test_run_index.py -q
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q
```

### Goal

实现 abstract screening + full-text screening 的 conservative two-stage pipeline，并与 abstract-only one-step、full-text one-step 做端到端对比。

### Tasks

- Stage 1 使用 high-sensitivity abstract-only screening，初始 baseline 使用 direct decision prompt；后续可比较 stricter direct prompt 或 softened criteria prompt。
- Stage 1 输出：
  - `exclude_low_risk`
  - `pass_to_full_text`
  - `unclear`
- `unclear` 和任何低置信、证据不足、不确定的 Stage 1 样本统一进入 Stage 2。
- Stage 2 使用 full-text 或 abstract+full-text screening；初始候选包括 raw criteria baseline 与 direct decision baseline。
- Stage 2 `unclear` 聚合为 `needs_review/include_for_review`，并在 safety evaluation 中按 include 处理。
- 计算 end-to-end metrics 和 full-text workload reduction。
- 输出 one-step vs two-stage 对照，至少包含：
  - direct one-step abstract+full-text baseline
  - raw criteria one-step abstract+full-text baseline
  - two-stage direct->raw criteria
  - 可选 two-stage direct->direct 或 direct->softened criteria

### Expected Outputs

- `code/screening/pipeline/two_stage.py`
- `code/screening/cli/run_two_stage.py`
- `results/preds/*/two_stage/*`
- `results/tables/one_step_vs_two_stage.csv`
- `results/reports/csmed_ft_two_stage_dev/summary.md`

### Acceptance Criteria

- end-to-end prediction 可以追溯 Stage 1 和 Stage 2 的中间结果。
- full-text workload = Stage 2 输入数量 / Stage 1 总输入数量。
- `needs_review` 在 final safety evaluation 中计为 include。
- Stage 1 不能因为缺失 abstract/full text、证据弱或模型不确定而自动 hard exclude。
- `one_step_vs_two_stage.csv` 必须同时报告 Sens、Spec、Bal Acc、Macro F1、TP/TN/FP/FN、Stage 2 workload 和 compared one-step baseline。
- 在成本允许时，需完成目标 benchmark 的正式真实 two-stage run，并产出 end-to-end metrics 与 workload reduction。

## Phase 10: Reason Quality Evaluation

**Progress:** `[ ]` Not started  
**Last Updated:** -  
**Notes:** -

### Goal

评估模型输出的 exclusion reason 是否准确、可审计，并且是否被 evidence span 支持。

### Tasks

- 实现 reason taxonomy：
  - `wrong_population`
  - `wrong_intervention`
  - `wrong_comparator`
  - `wrong_outcome`
  - `wrong_study_design`
  - `wrong_publication_type`
  - `not_primary_study`
  - `protocol_only`
  - `conference_abstract_only`
  - `duplicate_or_secondary_report`
  - `insufficient_data`
  - `indirect_evidence`
  - `other`
- 实现 predicted reason 到 taxonomy 的映射接口。
- 计算 reason category accuracy 和 reason macro F1。
- 导出 unsupported exclusion、hallucinated reason candidate 和 high-confidence FN 人评样本。
- 当前阶段不要求人工完成标注；只生成可选复核样本，用于后续分析。

### Expected Outputs

- `code/screening/evaluation/reasons.py`
- `results/tables/reason_quality.csv`
- `results/reports/human_eval_samples.jsonl`
- `results/reports/high_confidence_false_negatives.jsonl`
- `results/reports/unsupported_exclusion_cases.jsonl`

### Acceptance Criteria

- reason taxonomy 映射失败时输出 `other` 或 `unmapped`，不能丢弃样本。
- 所有 high-confidence FN 必须进入人工复核样本。
- unsupported/hallucinated reason 第一版可作为人工标注入口，不强制自动判定完全准确。
- 若当前目标是优先评估 LLM 效果，本阶段可以只输出 reason taxonomy、reason accuracy 和复核候选文件；人工标注结果不作为 Phase 11/12 的 blocker。

## Phase 11: Reporting And Error Analysis

**Progress:** `[ ]` Not started  
**Last Updated:** -  
**Notes:** -

### Goal

生成实验设计中需要的主结果表和错误分析报告，支持论文或阶段汇报。

### Tasks

- 汇总 Q2CRBench-3 abstract screening 表。
- 汇总 Q2CRBench-3 evidence-profile 辅助 setting 表；不得称为 full-text screening 主结果。
- 汇总 CSMeD-FT final screening 表。
- 汇总 one-step vs two-stage 表。
- 汇总 reason quality 表。
- 汇总 automation readiness 表，明确每个方法是否满足设计中的自动化阈值。
- 生成 `llm_effect_summary.md`，用简洁表格和结论回答：
  - abstract-only 是否足够安全
  - full-text/XML 是否提升 final screening
  - two-stage 是否在保持 sensitivity 的同时降低 full-text workload
  - 哪些方法产生了 false negative 或 high-confidence false negative
- 生成错误分析报告：
  - false negatives
  - high-confidence false negatives
  - unsupported exclusion reasons
  - criterion-level error distribution
  - full-text workload tradeoff

### Expected Outputs

- `code/screening/cli/build_tables.py`
- `results/tables/*.csv`
- `results/tables/*.md`
- `results/tables/automation_readiness.csv`
- `results/reports/error_analysis.md`
- `results/reports/llm_effect_summary.md`

### Acceptance Criteria

- 所有主表都能从 `run_index.csv` 找回输入和预测来源。
- 报告中明确列出自动化风险，尤其是 false negative 和 unsupported exclusion。
- 表格列名与 `experiment_design.md` 的结果报告模板保持一致。
- 报告必须区分真实 LLM 结果、mock/smoke test 结果和未运行方法；mock/smoke test 不进入主结论。

## Long-running And Deferred Work

以下工作不应混入基础框架阶段，除非用户明确要求：

- Q2CRBench-3 缺失记录的 search strategy 复现或作者数据请求。
- CSMeD-FT 通过 Semantic Scholar API、CORE API、GROBID、Cochrane Library cookie 和 PubMed Entrez email 重建全文。
- 大规模 LLM API 调用默认不混入基础框架阶段；正式真实实验应在 Phase 7-9 按用户指定范围执行。
- 多 provider、多模型完整对比。
- embedding retrieval、LLM reranking 和 prompt ablation。
- 全量 human evaluation；当前优先评估 LLM 效果，人工评测只作为后续可选质量分析。
- 论文级统计检验和显著性分析。

## Sync And Handoff Rules

每个 Phase 开始前：

- 读取本 TODO 的 `Progress Tracker` 和目标 Phase 小节。
- 检查当前 worktree，避免覆盖用户或其他阶段已有改动。
- 明确本阶段只完成当前 Phase 的目标，不顺手做后续阶段。

每个 Phase 完成后：

- 更新 `Progress Tracker`。
- 更新对应 Phase 的 `Progress / Last Updated / Notes`。
- 记录关键文件路径、生成结果路径和测试命令。
- 若阶段未完成，标记为 `[!] Blocked` 并写清楚 blocker、已完成部分和下一步需要的输入。

建议每次交接至少留下：

```text
Completed:
- ...

Key files:
- ...

Generated artifacts:
- ...

Validation:
- ...

Known blockers / next step:
- ...
```
