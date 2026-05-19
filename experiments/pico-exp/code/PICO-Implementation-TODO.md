# PICO Experiment Implementation TODO

本文档用于指导后续 Codex 按阶段实现 `PICO-Experiment-Plan.md`。目标不是一次性跑完所有实验，而是先搭好可复现的数据、评估和运行框架，再逐步接入 supervised baselines、LLM extraction 与 PICOX reproduction。

## Current Repo Facts

- 实验根目录：`/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/experiments/pico-exp`
- 实验 Python 环境：`/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv`
- 实验方案文档：`code/PICO-Experiment-Plan.md`
- EBM-NLP 数据包：`data/EBM-NLP/ebm_nlp_2_00.tar.gz`
- 本地模型：
  - `module/BiomedBERT-base-uncased-abstract-fulltext`
  - `module/BioLinkBERT-large`
- EBM-NLP 参考脚本：`code/external/ebm-nlp/`
- PICOX 参考 notebook：`code/external/picox/`
- 结果目录：`results/`
- Phase 1/2 当前状态：已完成项目骨架与 EBM-NLP official tar 数据加载；Phase 3 从 `results/data/*.examples.jsonl` 继续补 token offsets。

## Implementation Principles

- Official EBM-NLP tokenization 是唯一评估 token space。
- `end_token` 和 `char_end` 均使用 exclusive offset。
- Gold P/I/O spans 必须保留为独立多标签 span list；不能因为单序列 BIO 限制而丢弃 overlap。
- 第一版只做 `P/I/O`，不抽取单独 `C`。
- 第一版不加入 title，不做 full-text/section-aware modeling。
- 所有实验输出必须记录 config、seed、运行时间、输入数据版本和 evaluator 版本。
- 长时间训练、外部 API 调用、PICOX 全量复现应作为后续明确步骤执行，不要混在基础框架实现里。

## Experiment Directory Layout

本实验位于：

```text
/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/experiments/pico-exp
```

目录语义：

- `code/`: 本实验的代码、脚本和实验文档。
- `data/`: 本实验的数据。
- `module/`: 本实验使用的本地模型。
- `results/`: 本实验输出。

建议在本实验的 `code/` 目录下新增 Python package：

```text
pico-exp/
  code/
    PICO-Experiment-Plan.md
    PICO-Implementation-TODO.md
    config/
      llm_providers.example.yaml
    pico/
      __init__.py
      schemas.py
      paths.py
      config.py
      ebm_data.py
      offsets.py
      conversions.py
      evaluate.py
      validate_llm.py
      io_utils.py
      cli/
        __init__.py
        prepare_data.py
        evaluate_predictions.py
        validate_llm_predictions.py
        train_encoder.py
        run_llm.py
        run_picox.py
      tests/
        test_offsets.py
        test_conversions.py
        test_evaluate.py
        test_validate_llm.py
  data/
  module/
  results/
```

说明：

- `pico-exp/code/` 是本实验的代码目录。
- `pico-exp/code/pico/` 是 Python package，包名为 `pico`。
- 默认所有命令从 `pico-exp/` 实验根目录执行。
- 使用本项目环境中的 Python：`/F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python`。
- 从实验根目录运行 CLI 时，使用 `PYTHONPATH=code` 让 Python 找到 `code/pico/`。

默认运行方式：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.prepare_data --help
```

Phase 2 数据准备命令：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.prepare_data \
  --ebm-tar data/EBM-NLP/ebm_nlp_2_00.tar.gz \
  --output-dir results/data \
  --force
```

不要把 `code/` 当作 Python 包名使用；`code/` 只是本实验的代码目录，只通过 `PYTHONPATH=code` 加入模块搜索路径。

建议结果目录约定：

```text
results/
  data/
    manifests/
  preds/
  metrics/
  tables/
  logs/
  reports/
```

## Data And Result Organization Rules

本实验需要有规划地整理数据和结果，不能只保存零散输出。所有阶段的产物都应支持后续横向对比、复查和报告生成。

统一约定：

- `results/data/`: 保存标准化后的 train/test examples、gold spans、BIO labels 和数据质量摘要。
- `results/data/manifests/`: 保存数据索引和版本信息，例如 split、doc_id、token 数、gold span 数、overlap 情况。
- `results/preds/`: 保存各方法预测，按方法和设置分目录。
- `results/metrics/`: 保存各方法 evaluator 原始 JSON 指标，包含 TP/FP/FN 和质量指标。
- `results/tables/`: 保存统一对比表，优先同时输出 `.csv` 和 `.md`。
- `results/logs/`: 保存运行配置、命令、seed、模型版本、prompt/schema 版本和运行时间。
- `results/reports/`: 保存人工可读报告和错误分析样本。

建议统一表格：

- `results/tables/dataset_summary.csv`: split 级别数据统计。
- `results/tables/document_manifest.csv`: doc_id 级别索引，包含 split、token_count、P/I/O span counts、has_overlap。
- `results/tables/main_blurb_token_f1.csv`: BLURB-compatible token-level 对比表。
- `results/tables/main_span_f1.csv`: overlap-aware span-level 对比表。
- `results/tables/per_label_f1.csv`: P/I/O 分标签结果表。
- `results/tables/llm_quality.csv`: LLM JSON/offset/extractive/duplicate/overlap 质量表。
- `results/tables/run_index.csv`: 每次运行的 method、setting、config path、prediction path、metric path、timestamp。

每个方法的预测和指标都必须能通过 `run_index.csv` 找回对应输入、配置和输出。

建议新增配置文件模板：

```text
code/config/
  llm_providers.example.yaml
```

真实 key 后续由用户填写；不要把真实 key 提交到 git。

## Progress Tracker

后续每次让 Codex 执行时，先要求它读取并更新本节。状态只使用以下枚举：

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done
- `[!]` Blocked

| Phase | Status | Last Updated | Output / Notes |
|---|---|---|---|
| Phase 1: Project Skeleton | `[x]` | 2026-05-13 | Added `code/pico` package skeleton, shared schemas, JSON/JSONL I/O helpers, config loader, LLM provider template, and scaffolded `prepare_data` / `evaluate_predictions` CLIs. |
| Phase 2: EBM-NLP Data Loading | `[x]` | 2026-05-13 | Added tar-based Phase 2 loader and prepare CLI. Key files: `code/pico/ebm_data.py`, `code/pico/cli/prepare_data.py`, `code/tests/test_ebm_data.py`. Generated artifacts: `results/data/train.examples.jsonl`, `results/data/test.examples.jsonl`, `results/data/data_summary.json`, `results/data/manifests/document_manifest.csv`, `results/tables/dataset_summary.csv`, `results/tables/document_manifest.csv`. Actual counts: train 4794 docs / 1303076 tokens / 81956 PIO spans; test 191 docs / 51784 tokens / 4149 PIO spans. |
| Phase 3: Token Offset Mapping | `[x]` | 2026-05-13 | Added `code/pico/offsets.py`, integrated strict token-to-character alignment into `code/pico/ebm_data.py`, wrote offset failures to `results/data/offset_failures.jsonl`, and updated `prepare_data` to report `offset_failures=0` on the full EBM-NLP archive. Verified with `code/tests/test_offsets.py`, `code/tests/test_ebm_data.py`, and full `prepare_data` against `data/EBM-NLP/ebm_nlp_2_00.tar.gz`. |
| Phase 4: Gold Span And BIO Conversion | `[x]` | 2026-05-14 | Added `code/pico/conversions.py`, integrated overlap-preserving `gold_spans`, BLURB-compatible `bio_labels`, multi-label token coverage, and overlap conflict metadata. Regenerated `results/data/*.examples.jsonl`, `results/data/data_summary.json`, and summary/manifest CSVs. Full archive overlap counts: train 2827 docs / 21588 tokens; test 58 docs / 340 tokens. |
| Phase 5: Evaluators | `[x]` | 2026-05-14 | Added Phase 5 evaluator implementation and CLI. Key files: `code/pico/evaluate.py`, `code/pico/cli/evaluate_predictions.py`, `code/tests/test_evaluate.py`. Supports `--pred-format spans` and `--pred-format bio`, writes metrics JSON plus `main_blurb_token_f1.csv`, `main_span_f1.csv`, `per_label_f1.csv`, and `run_index.csv`. Verified with full local test suite: `31 passed`. |
| Phase 6: LLM Output Validator | `[x]` | 2026-05-14 | Added Phase 6 validator implementation and CLI. Key files: `code/pico/validate_llm.py`, `code/pico/cli/validate_llm_predictions.py`, `code/tests/test_validate_llm.py`. Validates raw per-document LLM JSON responses into strict official-token `Span` JSONL, records quality JSON, and appends `results/tables/llm_quality.csv`. Verified with full local test suite: `40 passed`. |
| Phase 7: Encoder BIO Baseline Entrypoint | `[!]` | 2026-05-14 | Deferred because the current environment has no GPU available. Keep the implementation notes below as the future GPU-backed plan; do not run encoder training in Phase 8. |
| Phase 8: LLM Runner Entrypoint | `[x]` | 2026-05-14 | Added OpenAI-first runner, text-only prompt mode, API key/model config documentation, dry-run support, text-only validator normalization, and text/content evaluator. Real API runs require a configured model id and API key. |
| Phase 9: PICOX Reproduction Entrypoint | `[ ]` | - | - |
| Phase 10: Reporting | `[ ]` | - | - |

每个 Phase 完成后，Codex 应同时更新：

- 对应 Phase 的 `Status / Last Updated / Output / Notes`
- 本文档中该 Phase 的 `Progress` 小节
- 若产生文件，写明关键文件路径
- 若有 blocker，使用 `[!]` 并写明下一步需要用户提供什么

## Phase 1: Project Skeleton

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-13  
**Notes:** Added package skeleton and Phase 1 contracts. Key files: `code/pico/__init__.py`, `code/pico/schemas.py`, `code/pico/io_utils.py`, `code/pico/config.py`, `code/pico/cli/prepare_data.py`, `code/pico/cli/evaluate_predictions.py`, `code/config/llm_providers.example.yaml`.

### Close-out

- `pico.schemas` defines `Span`, `DocumentExample`, `RunMetadata`, `PICO_LABELS`, and `LABEL_MAPPING`.
- `pico.io_utils` supports JSON/JSONL round trips for document examples, span predictions, metrics, and run metadata.
- `pico.config` loads provider config templates without storing real API keys.
- `prepare_data` is no longer a scaffold after Phase 2; `evaluate_predictions` remains a Phase 1 CLI contract for later evaluator work.
- Verified import/schema/I/O behavior during Phase 1 and re-verified `prepare_data --help` during Phase 2.

### Tasks

- 新建 `code/pico` Python package，包名为 `pico`。
- 定义通用 dataclass 或 typed dict：
  - `Span`
  - `DocumentExample`
  - `RunMetadata`
- 定义统一 label mapping：
  - `participants -> P`
  - `interventions -> I`
  - `outcomes -> O`
- 定义标准 JSONL I/O：
  - document examples
  - span predictions
  - metrics
  - run metadata
- 新增 LLM provider 配置模板，至少包含 OpenAI 与 DeepSeek 两个 provider 的 `api_key` 和 `base_url` 占位。

### Expected Outputs

- `code/pico/schemas.py`
- `code/pico/io_utils.py`
- `code/pico/config.py`
- `code/config/llm_providers.example.yaml`
- 基础 CLI 可执行，例如：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.prepare_data --help
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.evaluate_predictions --help
```

### Acceptance Criteria

- 从 `pico-exp/` 实验根目录执行时，可以用 `PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python` import `pico`。
- schema 字段与实验方案一致。
- JSONL read/write 能 round trip toy objects。
- LLM provider 配置模板存在，且不包含真实 key。

## Phase 2: EBM-NLP Data Loading

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-13  
**Notes:** Implemented `code/pico/ebm_data.py` as a direct tar reader for official `documents/*.txt`, `documents/*.tokens`, and aggregated `starting_spans` P/I/O labels. The loader validates binary label values and token-label length, stores raw labels in `DocumentExample.metadata`, and writes examples plus summary/manifest CSV artifacts. Phase 3 fills `token_offsets`; Phase 4 fills `gold_spans`, `bio_labels`, and overlap metadata. Official missing per-label `.ann` files are treated as empty all-zero label vectors after the document and token files are verified.

### Close-out

- Loader reads `data/EBM-NLP/ebm_nlp_2_00.tar.gz` directly with a streaming tar pass; it does not extract the full dataset.
- Required label sources:
  - train: `annotations/aggregated/starting_spans/{participants,interventions,outcomes}/train`
  - test: `annotations/aggregated/starting_spans/{participants,interventions,outcomes}/test/gold`
- Ignored sources: `test/crowd` and `hierarchical_labels`.
- Phase 2 examples originally kept `token_offsets`, `gold_spans`, and `bio_labels` empty; Phase 3 fills `token_offsets`; Phase 4 fills `gold_spans` and `bio_labels`.
- Raw labels are stored under `DocumentExample.metadata.pico_token_labels` as `P/I/O` binary vectors.
- Official absent per-label `.ann` files are treated as empty all-zero vectors, while absent document text/token files, invalid label values, and token-length mismatches fail the run.
- Span counts in Phase 2 are contiguous positive-run counts over starting-span binary labels; full span text and character offsets are now materialized by Phase 3/4.

Actual generated summary:

| Split | Docs | Tokens | P spans | I spans | O spans | Total PIO spans | Overlap docs |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 4794 | 1303076 | 16931 | 32313 | 32712 | 81956 | 2827 |
| test | 191 | 51784 | 632 | 1724 | 1793 | 4149 | 58 |

Validation run:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests/test_ebm_data.py -q
# 6 passed
```

### Tasks

- 支持从 `data/EBM-NLP/ebm_nlp_2_00.tar.gz` 读取或解压官方数据。
- 加载：
  - `documents/{pmid}.txt`
  - `documents/{pmid}.tokens`
  - `annotations/aggregated/starting_spans/{participants,interventions,outcomes}/{split}/...`
- split 处理规则：
  - train 使用 `train/`
  - test 主评估使用 `test/gold/`
  - `test/crowd/` 暂不进入主实验
- 解析 `.ann` 为 token-level binary labels。
- 校验每个 `.ann` 长度等于 official token 数。

### Expected Outputs

- `code/pico/ebm_data.py`
- CLI:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.prepare_data \
  --ebm-tar data/EBM-NLP/ebm_nlp_2_00.tar.gz \
  --output-dir results/data
```

- 产物：
  - `results/data/train.examples.jsonl`
  - `results/data/test.examples.jsonl`
  - `results/data/data_summary.json`
  - `results/data/manifests/document_manifest.csv`
  - `results/tables/dataset_summary.csv`
  - `results/tables/document_manifest.csv`

### Acceptance Criteria

- 输出 train/test 文档数量。
- 输出每个 split 的 P/I/O span 数量。
- 报告缺失文件、长度不匹配、空 annotation 的数量。
- `document_manifest.csv` 至少包含 `doc_id, split, token_count, p_span_count, i_span_count, o_span_count, total_span_count, has_overlap`。
- `dataset_summary.csv` 至少包含 `split, doc_count, token_count, p_span_count, i_span_count, o_span_count, overlap_doc_count`。
- 若有数据异常，程序应失败或写入明确 warning，不能静默跳过。

## Phase 3: Token Offset Mapping

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-13  
**Notes:** Added `code/pico/offsets.py` with strict exact token alignment and `OffsetAlignmentError`, integrated alignment into `prepare_data`, wrote failures to `results/data/offset_failures.jsonl`, and recorded offset failure statistics in `data_summary.json`. Full EBM-NLP preparation completed with `offset_failures=0`.

### Tasks

- 用 official `.tokens` 顺序对齐 `.txt`，生成每个 token 的 `(char_start, char_end)`。
- 对齐规则：
  - 按 token 顺序在 text 中查找 exact token。
  - 允许跳过 whitespace。
  - 对标点、括号、百分号、连字符等使用 exact substring matching，不做 normalize。
- 实现严格校验：
  - `abstract[char_start:char_end] == token`
  - offsets 单调递增
  - token 数一致

### Expected Outputs

- `code/pico/offsets.py`
- 每个 `DocumentExample` 包含 `token_offsets`。

### Acceptance Criteria

- 随机抽样至少 100 篇文档 offset 校验通过。
- 全量 prepare_data 时输出 offset failure count。
- offset 失败文档应写入 `results/data/offset_failures.jsonl`。

## Phase 4: Gold Span And BIO Conversion

**Progress:** `[x]` Completed  
**Last Updated:** 2026-05-14  
**Notes:** Added `code/pico/conversions.py` for official binary token labels -> overlap-preserving `gold_spans`, span coverage, BLURB-compatible `bio_labels`, conflict metadata, and diagnostic BIO -> span conversion. Integrated Phase 4 conversion into `code/pico/ebm_data.py`; prepared examples now retain raw `pico_token_labels`, include `multi_label_token_coverage`, and record BLURB overwrite policy `P -> I -> O` (`OUT > INT > PAR`) in `metadata.overlap_conflict`.

### Tasks

- 实现 `.ann token labels -> Span list`：
  - 连续 `1` 合并为一个 span。
  - span text 由 `char_start/char_end` 从 abstract 切出。
  - label 映射为 `P/I/O`。
- 实现 `Span list -> multi-label token coverage`。
- 实现 `Span list -> single BIO`：
  - 只用于 BLURB-compatible evaluation。
  - 如果同一 token 被多个 P/I/O label 覆盖，记录 overlap conflict。
- 实现 `BIO -> Span list`：
  - 仅用于 encoder baseline 诊断。

### Expected Outputs

- `code/pico/conversions.py`
- `results/data/*.examples.jsonl` 中包含：
  - `gold_spans`
  - `bio_labels`
  - `overlap_conflict` metadata

### Acceptance Criteria

- Toy tests 覆盖：
  - 单 span
  - 多 span
  - adjacent spans
  - P/I/O overlap
  - empty annotation
- 无 overlap 文档上，`spans -> BIO -> spans` 应保持 token boundary 和 label 一致。

## Phase 5: Evaluators

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Implemented `code/pico/evaluate.py` and replaced the Phase 1 evaluator CLI scaffold in `code/pico/cli/evaluate_predictions.py`. The evaluator supports both unified span JSONL predictions and per-document BLURB-compatible BIO JSONL predictions. Metrics include exact span micro/macro/per-label F1, relaxed span F1, overlap-subset exact F1, BLURB token micro/macro/per-label F1, TP/FP/FN counts, duplicate span accounting, evaluator version, input paths, method/setting/split metadata, and warnings.

### Close-out

- Span prediction input uses the existing `Span` JSONL schema.
- BIO prediction input uses one JSON object per document:

```json
{"doc_id": "...", "bio_labels": ["O", "I-PAR", "I-INT", "I-OUT"]}
```

- Missing prediction docs are treated as empty predictions: no spans for span evaluation, and all-`O` labels for token evaluation.
- Unknown prediction `doc_id`, illegal BIO labels, BIO length mismatches, invalid span labels, and out-of-range span token offsets fail the run.
- Exact span matching uses `(doc_id, label, start_token, end_token)` with multiset accounting; duplicate predictions beyond the matched gold instance count as FP and are reported under `exact_span.duplicates`.
- Relaxed span matching is one-to-one, same `doc_id` and label, with non-empty token interval overlap; candidates are greedily matched by descending overlap token count.
- Overlap-subset metrics are exact span metrics restricted to gold documents with `metadata.has_overlap == true`.
- Table writes use atomic CSV replacement. Existing rows with the same `method + setting + split + metric_name + prediction_path` fail by default; pass `--force` to replace.

Validation run:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q
# 31 passed
```

### Tasks

实现两套 evaluator。

BLURB-compatible token evaluator:

- token-level precision/recall/F1
- P/I/O per-label F1
- token Macro F1
- 忽略 overlap conflict 文档的规则只用于 LLM span 转 BIO 场景

PICOX-style span evaluator:

- exact span match：
  - same `doc_id`
  - same `label`
  - same `start_token`
  - same `end_token`
- micro precision/recall/F1
- macro F1 over P/I/O
- per-label F1
- overlap subset F1
- relaxed span F1，第一版可采用 token-overlap relaxed match，并在 metric metadata 里记录定义

### Expected Outputs

- `code/pico/evaluate.py`
- 每个 evaluator run 输出一份 JSON metric，并追加或生成统一表格行：
  - `results/tables/main_blurb_token_f1.csv`
  - `results/tables/main_span_f1.csv`
  - `results/tables/per_label_f1.csv`
  - `results/tables/run_index.csv`
- CLI:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.evaluate_predictions \
  --gold results/data/test.examples.jsonl \
  --pred results/preds/example.spans.jsonl \
  --pred-format spans \
  --output results/metrics/example.metrics.json \
  --method example \
  --setting default \
  --split test
```

BIO prediction example:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.evaluate_predictions \
  --gold results/data/test.examples.jsonl \
  --pred results/preds/example.bio.jsonl \
  --pred-format bio \
  --output results/metrics/example.bio.metrics.json \
  --method example \
  --setting bio \
  --split test
```

### Acceptance Criteria

- Unit tests 覆盖：
  - perfect prediction
  - missing span
  - extra span
  - wrong label
  - boundary too short/long
  - duplicate predictions
  - overlapping gold spans
- evaluator 输出中包含 TP/FP/FN counts，不能只输出 F1。
- 统一表格必须包含 `method, setting, split, metric_name, precision, recall, f1, tp, fp, fn, prediction_path, metric_path` 中适用字段。

## Phase 6: LLM Output Validator

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Implemented `code/pico/validate_llm.py` with `LLM_VALIDATOR_VERSION = "phase6-v1"` and the `validate_llm_predictions(examples, raw_rows)` API. Added `code/pico/cli/validate_llm_predictions.py` for raw response validation, strict span JSONL output, quality metrics JSON, and `results/tables/llm_quality.csv` upsert keyed by `method + setting + split + raw_path`. Invalid document responses are counted and skipped without stopping the batch. Duplicate valid spans keep the first instance only. Raw LLM runner output for Phase 8 must use one document response per JSONL line:

```json
{"doc_id": "10070173", "response": "[{\"label\":\"P\",\"text\":\"...\",\"char_start\":42,\"char_end\":78}]", "metadata": {}}
```

### Tasks

- 定义 LLM prediction JSON schema：

```json
[
  {
    "label": "P",
    "text": "...",
    "char_start": 42,
    "char_end": 78
  }
]
```

- 实现 raw response parser：
  - valid JSON only
  - schema validation
  - label must be P/I/O
- 实现 span validation：
  - offset 不越界
  - `abstract[char_start:char_end] == text`
  - char offsets 可映射到 official token offsets
  - duplicate span count
  - overlap conflict document/token count
- 若只输出 text 无 offset，标记为 weaker prompt ablation，不进入主 structured setting。

### Expected Outputs

- `code/pico/validate_llm.py`
- CLI:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.validate_llm_predictions \
  --examples results/data/test.examples.jsonl \
  --raw results/preds/llm/raw.jsonl \
  --valid-output results/preds/llm/validated.spans.jsonl \
  --quality-output results/metrics/llm_quality.json
```

### Acceptance Criteria

- 输出质量指标：
  - invalid JSON rate
  - schema invalid rate
  - non-extractive span rate
  - invalid offset rate
  - ambiguous match rate
  - duplicate span rate
  - overlap conflict document rate
  - overlap conflict token rate
- 对 invalid response 不应中断全批次处理，但必须计入质量指标。
- 验证命令：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pytest code/tests -q
# 40 passed

PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.validate_llm_predictions --help
```

## Phase 7: Encoder BIO Baseline Entrypoint

**Progress:** `[!]` Blocked / Deferred  
**Last Updated:** 2026-05-14  
**Notes:** Phase 7 is intentionally not implemented in this pass because the current environment has no GPU available. Keep this section as the future implementation contract. Do not run full encoder training until GPU access, final train/dev policy, and checkpoint selection rules are confirmed.

### Tasks

- 新增 `train_encoder.py` CLI，但第一版只需保证接口清晰。
- 支持参数：
  - model path
  - train examples
  - dev/test examples
  - output dir
  - seed
  - max length
  - batch size
  - learning rate
  - epochs
- 训练时使用 Hugging Face tokenizer/subword alignment。
- 评估时必须映射回 EBM-NLP official token BIO。
- 保存：
  - `pred.bio.jsonl`
  - `pred.spans.jsonl`
  - `metrics.json`
  - `run_config.json`

### Expected Outputs

- `code/pico/cli/train_encoder.py`
- 先跑 smoke test，不直接跑 full training。
- smoke run 后在 `results/tables/run_index.csv` 中新增一行，记录 config、prediction 和 metric 路径。

### Acceptance Criteria

- 小样本训练能完成 1 epoch。
- 输出 BIO 序列长度必须等于 official token 数。
- BiomedBERT 与 BioLinkBERT-large 使用相同 evaluator。

## Phase 8: LLM Runner Entrypoint

**Progress:** `[x]` Done  
**Last Updated:** 2026-05-14  
**Notes:** Implemented an OpenAI-first Phase 8 runner using the official `openai` Python package and Responses API structured output. The default LLM route is now text-only extraction (`zero-shot-text` / `few-shot-text`): the model outputs `label + text`, Phase 6 normalizes unique exact text matches into official token-space spans, and ambiguous matches are counted but not guessed. API key and model-id setup is documented in `code/config/OPENAI_API_CONFIG.md`; real keys must come from `OPENAI_API_KEY` or a local-only provider config.

### Tasks

- 新增 OpenAI-first `run_llm.py`。
- 第一版定义 prompt rendering、structured output schema、raw response 保存格式。
- 默认 structured output schema 只要求 `label + text`；offset-producing prompt 保留为 ablation。
- 使用官方 `openai` Python package。
- OpenAI 配置从环境变量或 YAML/JSON 文件读取，不要把 key 写死在代码里。
- 配置文件允许配置 `api_key_env`、可选 `api_key`、`base_url`、`temperature`、`timeout_seconds`。
- 不在无明确 model/api key/base_url 时真实调用 API；dry-run 不需要 key。
- prompt version、prompt schema 和 schema version 必须写入 metadata。
- 支持 zero-shot-text、few-shot-text、zero-shot-offsets 与 few-shot-offsets prompt mode。

建议配置模板：

```yaml
providers:
  openai:
    api_key_env: "OPENAI_API_KEY"
    api_key: "FILL_ME_OPENAI_API_KEY_OPTIONAL"
    model_id: "FILL_ME_OPENAI_MODEL_ID"
    model_version: null
    base_url: "https://api.openai.com/v1"
    timeout_seconds: 120
defaults:
  provider: "openai"
  temperature: 0
  timeout_seconds: 120
```

实际运行时通过 CLI 参数指定 provider 和 model：

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.run_llm \
  --provider openai \
  --model-id MODEL_ID \
  --provider-config code/config/llm_providers.yaml \
  --examples results/data/test.examples.jsonl \
  --output-dir results/preds/llm/openai_zero_shot \
  --prompt-mode zero-shot-text
```

### Expected Outputs

- `code/pico/cli/run_llm.py`
- `code/config/llm_providers.example.yaml`
- `code/config/OPENAI_API_CONFIG.md`
- prompt templates，例如：
  - `code/pico/prompts/zero_shot_text_v1.txt`
  - `code/pico/prompts/few_shot_text_v1.txt`
  - `code/pico/prompts/zero_shot_v1.txt`
  - `code/pico/prompts/few_shot_v1.txt`
- text/content evaluator:
  - `code/pico/text_evaluate.py`
  - `code/pico/cli/evaluate_text_predictions.py`
- LLM 运行后应更新：
  - `results/tables/run_index.csv`
  - `results/tables/llm_quality.csv`
  - `results/tables/main_span_f1.csv`
  - `results/tables/llm_text_f1.csv`
  - `results/tables/llm_pio_completeness.csv`
  - 如适用，`results/tables/main_blurb_token_f1.csv`

### Acceptance Criteria

- dry-run mode 能为指定样本生成 prompt JSONL。
- raw response 格式可被 Phase 6 validator 消费；text-only 唯一 exact match 会写入标准 span JSONL。
- metadata 包含 provider/model_id/model_version/api_date/base_url/temperature/prompt_version/prompt_schema/schema_version 字段。
- 缺少 key 或 base_url 时必须给出清晰错误；dry-run 不需要 key。
- 第一版只支持 `--provider openai`；DeepSeek/provider-neutral 扩展后置。
- text/content evaluator 输出 text exact/normalized F1 与 P/I/O completeness；official span track 只接受唯一 exact substring match，不猜 ambiguous 位置。

## Phase 9: PICOX Reproduction Entrypoint

**Progress:** `[ ]` Not started  
**Last Updated:** -  
**Notes:** -

### Tasks

- 阅读 `code/external/picox/*.ipynb`，整理 notebook 中的数据格式、模型步骤和 evaluator 输入输出。
- 新增 `run_picox.py`，第一版可以只做：
  - EBM-NLP examples -> PICOX expected input conversion
  - PICOX output -> unified span list conversion
- 不改变 PICOX boundary detector/span classifier 核心假设。
- 若未完全复用官方 pipeline，结果名称必须是 `PICOX-compatible`，不能写 `official reproduction`。

### Expected Outputs

- `code/pico/cli/run_picox.py`
- `results/preds/picox/*.spans.jsonl`
- `results/metrics/picox/*.metrics.json`
- PICOX 运行后应更新：
  - `results/tables/run_index.csv`
  - `results/tables/main_span_f1.csv`
  - `results/tables/per_label_f1.csv`

### Acceptance Criteria

- 转换脚本能处理至少一个 toy/sample 文件。
- 输出 span list 可被 Phase 5 evaluator 直接评估。
- run metadata 明确记录 reproduction status。

## Phase 10: Reporting

**Progress:** `[ ]` Not started  
**Last Updated:** -  
**Notes:** -

### Tasks

- 汇总指标为标准表：
  - Table A: BLURB-compatible token Macro F1
  - Table B: overlap-aware span evaluation
  - LLM quality table
  - per-label table
- 从 `results/tables/*.csv` 生成对应 Markdown 表格，避免手工复制指标。
- 维护 `results/tables/run_index.csv`，作为所有实验运行的总索引。
- 错误分析抽样：
  - test set 抽样 100 篇 abstract
  - 每篇保留 gold/pred spans 和原文 offset
  - 人工标注错误类型
- 生成实验报告 markdown。

### Expected Outputs

- `results/tables/main_blurb_token_f1.csv`
- `results/tables/main_blurb_token_f1.md`
- `results/tables/main_span_f1.csv`
- `results/tables/main_span_f1.md`
- `results/tables/per_label_f1.csv`
- `results/tables/per_label_f1.md`
- `results/tables/llm_quality.csv`
- `results/tables/llm_quality.md`
- `results/tables/run_index.csv`
- `results/reports/main_tables.md`
- `results/reports/error_analysis_sample.jsonl`
- `results/reports/final_report.md`

### Acceptance Criteria

- 报告明确区分：
  - benchmark-comparable token-level result
  - span-extraction result
  - overlap-aware result
- 报告列出所有 model/config/seed/checkpoint selection rules。
- LLM 结果必须同时报告 F1 和质量指标。
- `results/reports/main_tables.md` 必须由 `results/tables/` 中的统一表格生成或同步，不能和 CSV 指标不一致。

## Suggested Execution Order

1. Phase 1: Project skeleton
2. Phase 2: EBM-NLP data loading
3. Phase 3: Token offset mapping
4. Phase 4: Gold span and BIO conversion
5. Phase 5: Evaluators
6. Phase 6: LLM validator
7. Phase 7: Encoder baseline smoke run
8. Phase 8: LLM dry-run and then real run after model is fixed
9. Phase 9: PICOX conversion and reproduction
10. Phase 10: Reporting

## First Codex Prompt Recommendation

下一步建议给 Codex 的任务：

```text
请按照 code/PICO-Implementation-TODO.md 执行 Phase 1-2：
1. 创建 code/pico 包和基础 schemas/io_utils；
2. 实现从 data/EBM-NLP/ebm_nlp_2_00.tar.gz 读取 documents/tokens/aggregated starting_spans 的 data loader；
3. 先不要训练模型，不要调用 LLM，不要跑 PICOX；
4. 增加最小测试或 smoke command，证明 train/test examples 可以生成。
```
