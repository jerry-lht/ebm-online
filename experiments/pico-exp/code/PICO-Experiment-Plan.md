# EBM-NLP PICO Span 抽取实验方案

## Summary

本实验评测 `RCT abstract -> P/I/O spans`。数据集采用 EBM-NLP / EBM PICO，任务标签与官方保持一致：

- `P = Participants`
- `I = Interventions / Controls`
- `O = Outcomes`

第一版只关注 `P/I/O`，不单独抽取 `C`。Control/comparator 若被标注，按 EBM-NLP 的 `Interventions` 处理，不展开 hierarchical subtype。

核心问题是：

> 特定 LLM 在 RCT 摘要 PICO span 抽取上，是否能达到或超过传统 biomedical encoder 与 span-based extractor？

## Experimental Setup

数据使用 EBM-NLP / EBM PICO。优先使用官方 GitHub 原始数据结构，BigBio / Hugging Face `ebm_pico` 可作为加载和格式校验的备选来源。

主实验 split 固定为 BLURB EBM PICO split，以保证 word/token-level Macro F1 可与 BLURB benchmark 口径对齐。EBM-NLP 原始 split 只能作为额外 robustness setting；不同 split 的结果不能放在同一主表中直接比较。

当前实现进度截至 2026-05-14：

| Phase | Status | Implemented Scope |
|---|---|---|
| Phase 1: Project Skeleton | Done | 已建立 `code/pico` package、共享 schema、JSON/JSONL I/O、配置模板和基础 CLI。 |
| Phase 2: EBM-NLP Data Loading | Done | 已实现官方 EBM-NLP tar 包直接读取、train/test examples 输出、数据摘要和 manifest 表。 |
| Phase 3: Token Offset Mapping | Done | 已将 official tokens 严格对齐到 abstract character offsets，full archive offset failure count 为 0。 |
| Phase 4: Gold Span And BIO Conversion | Done | 已生成 overlap-preserving `gold_spans`、BLURB-compatible `bio_labels`、multi-label coverage 和 overlap metadata。 |
| Phase 5: Evaluators | Done | 已实现 `code/pico/evaluate.py` 和 `pico.cli.evaluate_predictions`，支持 span JSONL 与 BIO JSONL，输出 metrics JSON 和统一 CSV 表。 |

当前数据加载使用官方 EBM-NLP archive 内的原始 train/test 标注结构：

```text
data/EBM-NLP/ebm_nlp_2_00.tar.gz
ebm_nlp_2_00/documents/{pmid}.txt
ebm_nlp_2_00/documents/{pmid}.tokens
ebm_nlp_2_00/annotations/aggregated/starting_spans/{participants,interventions,outcomes}/train
ebm_nlp_2_00/annotations/aggregated/starting_spans/{participants,interventions,outcomes}/test/gold
```

`test/crowd` 与 `hierarchical_labels` 暂不进入主数据产物。Phase 3/4 已在 official token space 上补齐 token-to-character offsets、gold span text、overlap-preserving span list、single-sequence BIO labels 和 overlap metadata。

输入统一为 official abstract text：

```text
RCT abstract only
```

不额外补全 title。若后续研究希望加入 title，只能作为单独 ablation，并明确标注为 not benchmark-comparable。

主实验标签源固定为 EBM-NLP aggregated P/I/O annotations：

```text
aggregated/starting_spans/participants
aggregated/starting_spans/interventions
aggregated/starting_spans/outcomes
```

第一版不使用 hierarchical labels；如果后续使用 hierarchical labels，必须显式记录 subtype collapse rule。

输出统一为 span list：

```json
[
  {
    "doc_id": "...",
    "label": "P",
    "text": "...",
    "start_token": 10,
    "end_token": 15,
    "char_start": 42,
    "char_end": 78
  }
]
```

数据处理中保留两种表示：

| 表示 | 用途 |
|---|---|
| BIO token labels | 用于 token classification baseline |
| Span list | 用于所有方法统一评估 |

token space 固定为 EBM-NLP 官方 tokenization；`end_token` 与 `char_end` 均使用 exclusive offset。模型 tokenizer / subword alignment 只作为训练细节，不能改变 evaluator token space。

由于 EBM-NLP 存在少量 P/I/O 重叠标注，gold annotations 应保留 P/I/O 独立 span。单序列 BIO 只能用于 BLURB-compatible 评价；overlap-aware 评价必须使用能表达多标签 span 的输出格式。

当前数据契约：

- 每篇文档输出为一个 `DocumentExample`。
- `abstract` 来自官方 `documents/{pmid}.txt`。
- `tokens` 来自官方 `documents/{pmid}.tokens`。
- `metadata.pico_token_labels` 保存 `P/I/O` 三组 token-level binary labels。
- `metadata.source_paths` 保存原始 archive 内路径；若某个 per-label `.ann` 在官方 aggregated starting-span 目录中缺失，则表示该 label 没有正例 starting span，加载器记录为 `None` 并生成全零 label vector。
- `token_offsets` 保存 official token 到 abstract 的 strict character offsets。
- `gold_spans` 保存 overlap-preserving P/I/O spans。
- `bio_labels` 保存 BLURB-compatible single-sequence labels，使用 Phase 4 记录的 overwrite policy。

已生成数据统计：

| Split | Docs | Tokens | P spans | I spans | O spans | Overlap docs |
|---|---:|---:|---:|---:|---:|---:|
| train | 4794 | 1303076 | 16931 | 32313 | 32712 | 2827 |
| test | 191 | 51784 | 632 | 1724 | 1793 | 58 |

当前产物：

- `results/data/train.examples.jsonl`
- `results/data/test.examples.jsonl`
- `results/data/data_summary.json`
- `results/data/manifests/document_manifest.csv`
- `results/tables/dataset_summary.csv`
- `results/tables/document_manifest.csv`

## Methods

本实验比较三类方法，而不是提前假设某组训练参数最优。

### 1. Biomedical Encoder + BIO Tagging

代表方法：

| Method | Model |
|---|---|
| BiomedBERT | `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` |
| BioLinkBERT-large | `michiyasunaga/BioLinkBERT-large` |

作用：

- 作为标准 supervised biomedical NER baseline。
- 与 BLURB / EBM PICO 的历史 benchmark 口径保持可比。
- 输出单序列 BIO labels，用 BLURB-compatible evaluator 评价。
- 另外把 BIO labels 转换为 span list，参与非重叠 span 诊断；但单序列 BIO 不用于衡量重叠部分上限。

训练策略：

- 优先参考 BLURB、模型论文、官方示例或公开复现代码中的 fine-tuning 设置。
- 若无完全一致设置，则使用合理的小范围 dev-set tuning。
- 不在实验方案中预设“最佳超参数”，而是在实验记录中完整保存搜索空间、最终参数、seed、checkpoint 选择规则和硬件环境。

### 2. Span-based Extractor

代表方法：

```text
PICOX
```

作用：

- 作为 span-level PICO extraction baseline。
- 重点比较 BIO tagging 与 span boundary / span classification 范式的差异。
- 第一版计划基于 PICOX 原仓库相关代码复现官方 pipeline，不做结构性魔改。

实验要求：

- 优先使用 PICOX 原仓库代码中的 preprocessing、boundary detector、span classifier 和 evaluation pipeline。
- 如果需要适配 EBM-NLP 格式，只做数据格式转换，不改变核心模型假设。
- 同时把 PICOX 输出转为统一 span list，用同一个 evaluator 重新评估。
- 只有在使用 PICOX 原仓库代码、preprocessing、split / data mapping、post-processing 和 evaluation pipeline 时，结果才称为 `PICOX official reproduction`。
- 若只是复用其 overlap-aware entity/span-level 评价思想，则结果称为 `PICOX-compatible` 或 `PICOX paper-style`，不能称为 official evaluation。

### 3. Specific LLM Structured Extraction

LLM 暂不指定为 GPT-5.5，实验中记为：

```text
Target LLM
```

最终运行前必须锁定并记录：

```text
provider
model_id
model_version 或 release date
API date
temperature / decoding setting
prompt version
schema version
```

设置包括：

| Setting | Description |
|---|---|
| Zero-shot | 只给任务说明，不给示例 |
| Few-shot | 给 3-5 个 train/dev 示例 |
| Structured JSON | 强制输出 JSON span list |
| Optional free-form ablation | 检查 schema 约束是否减少非法输出 |

LLM 输出要求：

```text
1. Only extract exact text spans from the input.
2. Do not paraphrase.
3. Do not infer missing information.
4. Use only P/I/O labels.
5. Return valid JSON only.
```

LLM JSON schema 要求同时返回 text 与 character offsets：

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

输出后用程序校验：

1. `abstract[char_start:char_end]` 必须与 `text` 完全一致。
2. char offsets 必须能映射到 EBM-NLP official token offsets。
3. 无法校验的 span 计入 `non-extractive span rate` 或 `invalid offset rate`。
4. 若只输出 text 而无 offset，该设置只能作为 weaker prompt ablation，并记录 ambiguous string match rate。

## Evaluation

本实验报告两套评价，分别回答不同问题：

| Evaluation Track | Purpose | Gold / Prediction Form |
|---|---|---|
| BLURB-compatible single-sequence evaluation | 对齐 EBM-NLP / BLURB token-level benchmark | 单序列 BIO / token labels |
| PICOX-style overlap-aware span evaluation | 评价 P/I/O 重叠 span 与边界抽取能力 | 多标签 span list |

Phase 5 evaluator 已实现为：

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

预测输入支持两种格式：

- `--pred-format spans`: 每行一个 `Span` JSON object，字段包含 `doc_id, label, text, start_token, end_token`，可选 `char_start, char_end, score, metadata`。
- `--pred-format bio`: 每行一个 document BIO JSON object，例如 `{"doc_id": "...", "bio_labels": ["O", "I-PAR", "I-INT"]}`。

evaluator 输出原始 metrics JSON，并维护以下 CSV 表：

- `results/tables/main_blurb_token_f1.csv`
- `results/tables/main_span_f1.csv`
- `results/tables/per_label_f1.csv`
- `results/tables/run_index.csv`

单序列 BIO 可以用 BLURB-compatible evaluator 评价；但它无法表示同一 token 的多个 P/I/O 标签。因此重叠部分不能用 PICOX-style evaluator 来“补救”单序列 BIO，只能用 PICOX 或 LLM 等能输出多标签 span list 的方法参与 overlap-aware 评价。

LLM span 输出转换为 BLURB-compatible single BIO 时采用保守规则：

1. 先将可校验的 LLM spans 映射到 EBM-NLP official token space。
2. 若任一 token 被多个 P/I/O labels 覆盖，则该 document 标记为 `overlap conflict`。
3. 含 `overlap conflict` 的 document 不进入 LLM 的主 BLURB-compatible score。
4. 额外报告 `LLM overlap conflict document rate` 与 `LLM overlap conflict token rate`。

该规则避免人为选择 `P > I > O` 等优先级带来的偏置；代价是 BLURB-compatible LLM score 只反映无冲突样本上的单序列表现。

span 主指标是 span-level exact-match F1，因为本任务目标是抽取可用的 PICO span。

Exact match 要求：

```text
label 相同
start_token 相同
end_token 相同
```

同时报告：

| Metric | Purpose |
|---|---|
| EBM-NLP Token Macro F1 | 对齐 EBM-NLP / BLURB benchmark |
| Span Micro F1 | 主结果，衡量整体抽取能力 |
| Span Macro F1 | 平衡 P/I/O 三类 |
| P/I/O per-label F1 | 分析不同 PICO 元素难度 |
| Relaxed Span F1 | 辅助分析边界偏差 |
| Invalid JSON Rate | LLM 输出合法性 |
| Non-extractive Span Rate | LLM 是否产生非原文 span |
| Invalid Offset Rate | LLM offset 是否无法校验 |
| Duplicate Span Rate | LLM 是否重复抽取 |
| Over-generation Rate | LLM 是否输出过多无关 span |

LLM 输出质量指标是必须报告项，不能只报告 F1：

| LLM Quality Metric | Definition |
|---|---|
| Invalid JSON Rate | response 不能解析为要求的 JSON schema |
| Non-extractive Span Rate | 返回的 `text` 不是 abstract 中的 exact substring |
| Invalid Offset Rate | `char_start` / `char_end` 越界，或 `abstract[char_start:char_end] != text` |
| Ambiguous Match Rate | 未提供有效 offset 且 `text` 在 abstract 中出现多次 |
| Duplicate Span Rate | 同一 `label + char_start + char_end` 被重复输出 |
| Over-generation Rate | 输出 span 数量明显超过 gold 或包含无关 P/I/O 外内容；具体阈值在 evaluator 中固定并记录 |
| Overlap Conflict Rate | LLM spans 转 single BIO 时产生多标签 token 冲突的 document / token 比例 |

主实验表 A：BLURB-compatible single-sequence evaluation

| Method | Paradigm | Training Data | Output Normalization | EBM-NLP Token Macro F1 |
|---|---|---:|---|---:|
| BiomedBERT | single BIO tagging | full train | native BIO | |
| BioLinkBERT-large | single BIO tagging | full train | native BIO | |
| Target LLM zero-shot | structured LLM | none | span -> single BIO | |
| Target LLM few-shot | structured LLM | 3-5 examples | span -> single BIO | |

主实验表 B：PICOX-style overlap-aware span evaluation

| Method | Paradigm | Training Data | Output | Span Micro F1 | Span Macro F1 | Overlap Subset F1 |
|---|---|---:|---|---:|---:|---:|
| PICOX | span-based | full train | multi-label span | | | |
| Target LLM zero-shot | structured LLM | none | JSON span | | | |
| Target LLM few-shot | structured LLM | 3-5 examples | JSON span | | | |

BiomedBERT / BioLinkBERT single BIO 可额外报告转换后的 span F1 作为诊断结果，但不能作为 overlap-aware 主结果。若需要让 encoder 参与表 B，必须增加 three-head / multi-label token classifier 或 span classifier。

## Ablation And Analysis

建议做 3 个核心 ablation：

| Ablation | Purpose |
|---|---|
| Zero-shot vs few-shot | 判断示例是否改善边界和标签一致性 |
| Strict JSON schema vs weaker prompt | 判断结构约束是否减少 invalid / paraphrase |
| Token-level vs span-level metric | 证明 token-level 分数不等价于 span 抽取质量 |

建议增加 1 个 overlap 相关 ablation：

```text
single BIO tagging vs multi-head token classification
```

这个 ablation 用于判断传统 encoder 在 P/I/O overlap 上的上限。如果第一版时间有限，可以只报告 single BIO + PICOX + LLM，但必须在报告中说明 single BIO 无法表达重叠标签。

错误分析从 test set 抽样 100 篇 abstract，人工归类：

| Error Type | Description |
|---|---|
| boundary too short | span 边界过短 |
| boundary too long | span 边界过长 |
| label confusion | P/I/O 混淆 |
| missing outcome | 漏抽 outcome |
| intervention-control ambiguity | 干预与对照处理不一致 |
| hallucinated/paraphrased span | LLM 输出非原文 span |
| duplicate extraction | 重复抽取 |
| ambiguous string match | LLM span 在原文中出现多次，offset 不唯一 |

## Reproducibility Rules

实验方案不预设具体训练参数为“最佳值”。所有监督模型和 PICOX 的参数处理遵循以下优先级：

1. 优先使用原论文、官方代码或 BLURB 公开设置。
2. 若公开设置不完整，则定义小范围 dev-set tuning。
3. 所有 tuning 只能基于 train/dev，不能查看 test。
4. 最终报告必须记录完整搜索空间、最终参数、seed、checkpoint 选择规则、硬件环境和运行日期。
5. LLM 实验必须记录 model id、版本、prompt、schema、decoding setting 和 API 日期。

## Execution Order

1. 已完成项目骨架、共享 schema、I/O helpers、配置模板与基础 CLI。
2. 已完成 EBM-NLP Phase 2 数据加载，生成 official train/test examples、summary 和 manifest。
3. 下一步完成 token offset mapping、gold span list 和 BIO labels。
4. 实现 BLURB-compatible evaluator 与 PICOX-style overlap-aware evaluator，先用 toy examples 验证 exact / relaxed / token-level 指标。
5. 跑 BiomedBERT 与 BioLinkBERT-large supervised baselines。
6. 跑 Target LLM zero-shot 与 few-shot structured extraction。
7. 复现 PICOX official pipeline。
8. 汇总主实验表、分标签表、LLM 质量表和错误分析表。
9. 写实验报告，明确区分 benchmark-comparable 结果与 span-extraction 结果。

## Assumptions

- 第一版不加入 title / 全文，不做 section-aware 建模。
- 第一版不单独抽取 `C`。
- 第一版主标签源为 aggregated starting spans 的 P/I/O。
- Target LLM 尚未确定，实验方案中统一使用占位名。
- 训练参数不在方案中写死，除非来自可引用的原始实验设置或后续 dev-set tuning。
- 参考来源包括 EBM-NLP、BigBio `ebm_pico`、BLURB、PICOX 与既有 biomedical LLM benchmark。
