# LLM 用于循证医学 Study Screening 的实验设计

## 1. 研究背景与目标

系统综述和循证医学证据合成通常需要对大量候选文献进行 study screening，即根据 review question、PICO/PICOS 和纳入排除标准判断候选研究是否应进入后续分析。传统人工筛选成本高、耗时长，并且需要较高领域专业知识。本实验拟评估 criteria-aware LLM 是否能够辅助或部分自动化完成这一排纳任务。

本实验关注的任务定义如下：

```text
Input:
- Candidate studies
- Review / clinical question
- PICO / PICOS
- Inclusion criteria
- Exclusion criteria
- Title / abstract
- Optional full text, preferably XML-sectioned full text

Output:
- final decision: include / exclude
- exclusion reason, if excluded
- criterion-level judgments
- supporting evidence span
```

实验最终回答三个核心问题：

1. LLM 仅基于 title/abstract 是否能够安全完成初筛？
2. LLM 使用 full text 或 XML-sectioned full text 后，是否能够获得更高的 final include/exclude 准确性？
3. 两阶段 pipeline 是否比单阶段方法更适合自动化排纳场景？

本实验的核心 claim 可以表述为：

> We evaluate whether criteria-aware LLMs can perform automated study screening for evidence synthesis. We test abstract-only screening, full-text XML-section screening, and a conservative two-stage pipeline on Q2CRBench-3 and CSMeD-FT.

中文表述为：

> 我们评估 criteria-aware LLM 是否能够自动完成循证医学中的 study screening。实验覆盖摘要初筛、基于 XML section 的全文筛选，以及保守两阶段 pipeline，并在 Q2CRBench-3 和 CSMeD-FT 上验证。

## 2. Benchmark 选择

### 2.1 数据来源

本实验只使用公开 benchmark 数据，不使用项目中其他本地 Cochrane 文件夹作为实验数据来源。两个 benchmark 的来源如下：

| Benchmark | 在线来源 | 本实验用途 |
| --- | --- | --- |
| Q2CRBench-3 | Hugging Face: `somewordstoolate/Q2CRBench-3` | PICO-driven abstract screening、full-text/evidence-profile screening、two-stage pipeline 评估 |
| CSMeD-FT | GitHub: `WojciechKusa/systematic-review-datasets`；baseline repo: `WojciechKusa/CSMeD-baselines` | systematic review full-text screening 泛化验证 |

### 2.2 Q2CRBench-3

Q2CRBench-3 是本实验的主 benchmark。该数据集发布在 Hugging Face，来源于三份临床指南开发记录，用于评估 LLM 生成临床推荐和处理 evidence screening 相关任务的能力。

本实验中 Q2CRBench-3 主要用于：

- 验证 LLM 是否能够完成基于 PICO/PICOS 和 criteria 的 title/abstract screening。
- 比较 abstract-only 与 full-text / evidence-profile 输入的筛选效果。
- 验证两阶段 screening pipeline 的合理性。

本实验主要使用其中与筛选任务相关的信息：

```text
review / clinical question
PICO / PICOS
study design requirement
candidate records with title / abstract
paper-level evidence profile or available full-text evidence
gold screening labels
```

其中，question、PICO/PICOS 和 study design requirement 用作模型筛选标准；candidate records 用于 abstract screening；paper-level evidence profile 或可获得的全文证据用于 full-text screening。

需要注意，Q2CRBench-3 数据页说明，由于版权限制，2020 EAN Dementia 和 2021 ACR RA 的部分筛选记录不能直接完整提供，需要通过 search strategies 复现或向作者请求。因此实验开始前必须先确认目标 review question 的候选记录与 gold labels 是否完整；缺失部分不能直接纳入主实验，只能作为待补充数据。

### 2.3 CSMeD-FT

CSMeD-FT 是用于 full-text publication screening 的 benchmark，适合作为外部验证集，用来检验方法是否能够泛化到 systematic review full-text screening 场景。CSMeD 论文说明其整合了 325 个 SLR，并额外引入 CSMeD-FT 用于 full-text publication screening。作者 GitHub 仓库提供 CSMeD 与 CSMeD-FT 的数据加载、构建和 baseline 代码。

本实验中 CSMeD-FT 主要用于：

- 验证 LLM 在 full-text screening 上的 final include/exclude 能力。
- 验证 exclusion reason generation 的质量。
- 比较 abstract-only、full-text XML 和 abstract + full-text XML 三类输入设置。

使用的数据划分为：

```text
CSMeD-FT-train
CSMeD-FT-dev
CSMeD-FT-test
CSMeD-FT-test-small
```

作者仓库给出的 CSMeD-FT 规模如下：

| Split | #reviews | #docs | #included | %included | Avg. #words in document |
| --- | ---: | ---: | ---: | ---: | ---: |
| CSMeD-FT-train | 148 | 2053 | 904 | 44.0% | 4535 |
| CSMeD-FT-dev | 36 | 644 | 202 | 31.4% | 4419 |
| CSMeD-FT-test | 29 | 636 | 278 | 43.7% | 4957 |
| CSMeD-FT-test-small | 16 | 50 | 22 | 44.0% | 5042 |

CSMeD-FT 的全文数据构建需要额外依赖，包括 Semantic Scholar API、CORE API 和 GROBID；作者也说明最少需要 Cochrane Library cookie 和 PubMed Entrez email 才能构建数据。因此实验前需要先完成数据下载与解析检查。

## 3. 总体实验结构

本实验采用一个两阶段 pipeline，并保留单阶段方法作为对照。

### 3.1 Stage 1: Abstract Screening

Stage 1 只使用候选文献的 title 和 abstract，目标是判断文献是否应进入全文筛选。

输入：

```text
Clinical / review question
PICO / PICOS
Inclusion criteria
Exclusion criteria
Title
Abstract
```

输出：

```text
pass_to_full_text / exclude
reason
criterion-level judgments
evidence spans
```

Stage 1 的核心要求是高 sensitivity。由于初筛阶段的主要风险是漏掉应纳入研究，因此在自动化标准中 false negative 比 false positive 更重要。

### 3.2 Stage 2: Full-text Screening

Stage 2 使用 full text 或 XML-sectioned full text，目标是做最终 include/exclude 判断。

输入：

```text
Clinical / review question
PICO / PICOS
Inclusion criteria
Exclusion criteria
XML-sectioned full text
```

输出：

```text
final include / exclude
exclusion reason
criterion-level judgments
evidence spans
```

Stage 2 的目标是在保持高 sensitivity 的基础上，提高 specificity、precision 和 reason support rate。

### 3.3 Two-stage Decision

两阶段 pipeline 的基本决策规则为：

```text
If Stage 1 = exclude:
  final = exclude

If Stage 1 = pass_to_full_text:
  final = Stage 2 decision
```

保守版本采用以下规则：

```text
If Stage 1 uncertain:
  pass_to_full_text

If Stage 2 uncertain:
  include / needs_review
```

在实验评测中，`needs_review` 可统一视为 `include`，以模拟安全排纳策略。也就是说，不确定样本不被自动排除。

## 4. 方法设计

### 4.1 Strong Baseline: Direct Criteria-aware LLM

Direct Criteria-aware LLM 是本实验的强 baseline。该方法不需要训练，也不依赖传统机器学习特征工程，而是直接将 review question、PICO/PICOS、criteria 和候选研究内容输入 LLM，让模型输出结构化判断。

输入模板如下：

```text
Clinical / review question:
{question}

PICO / PICOS:
Population: {P}
Intervention / Exposure: {I}
Comparator: {C}
Outcome: {O}
Study design: {S}

Inclusion criteria:
{inclusion_criteria}

Exclusion criteria:
{exclusion_criteria}

Candidate study:
Title: {title}
Abstract: {abstract}

Full text sections if available:
{xml_sections}
```

输出 schema 如下：

```json
{
  "decision": "include | exclude",
  "confidence": 0.0,
  "criterion_judgments": {
    "population": "yes | no | unclear",
    "intervention": "yes | no | unclear",
    "comparator": "yes | no | unclear | not_applicable",
    "outcome": "yes | no | unclear",
    "study_design": "yes | no | unclear"
  },
  "main_reason": "...",
  "failed_criterion": "...",
  "evidence_spans": ["..."]
}
```

该 baseline 测试三种输入设置：

| Setting | Input |
| --- | --- |
| Abstract-only | question + PICO/PICOS + criteria + title + abstract |
| Full-text-only | question + PICO/PICOS + criteria + XML sections |
| Abstract + full-text | question + PICO/PICOS + criteria + title + abstract + XML sections |

该方法用于回答：

- 只看 abstract 是否足够安全？
- full text 是否能提高筛选效果？
- criteria-aware prompt 是否能直接完成排纳判断？

### 4.2 Main Method: Criterion-wise Evidence-grounded LLM

主方法不把 XML section 映射写死，而是把 full text 或 XML-sectioned text 当作可检索的 evidence pool。模型先为每个 screening criterion 找到可能相关的段落，再分别判断每个 criterion 是否满足，最后根据 criterion-level judgments 聚合为最终 include/exclude。

该方法要验证两个问题：

1. 只传入与当前 criterion 相关的段落，是否比直接输入全文更稳定、更可解释。
2. 先输出不同 criterion 的判断，再聚合 final decision，是否比模型直接输出 final include/exclude 更可靠。

#### 4.2.1 Evidence Candidate Selection

由于不同数据源的 XML sections 命名不稳定，不能假设一定存在标准的 Methods、Participants、Outcomes 等字段。因此 evidence selection 只定义思路，不固定为某一套 section 名称。

候选 evidence 的来源包括：

```text
Title
Abstract
Structured XML sections, if available
Review full-text sections
Evidence profile text
Study characteristics text
References / included-study descriptions, if available
```

对每个 criterion，先从候选文本中选择 top-k 个相关段落。选择方式可以是以下一种或多种：

| Selection strategy | Description |
| --- | --- |
| Section-title heuristic | 根据 section title 与 criterion 的语义相似度选择候选段落 |
| Keyword / rule matching | 使用 PICO terms、study-design terms、intervention/comparator/outcome keywords 检索段落 |
| Embedding retrieval | 将 criterion query 与段落向量匹配，选择 top-k evidence candidates |
| LLM reranking | 先召回较多候选段落，再让 LLM 判断哪些段落真正支持该 criterion |

这里的 XML mapping 只作为候选召回的弱规则，而不是 hard-coded 方法。第一版实验先观察原始数据集中已有 full text / section / evidence profile 的直接表现；如果结果显示 section 命名或段落质量明显影响性能，再单独加入数据清洗或 section routing 实验。

#### 4.2.2 Criterion-wise Judgment

在得到每个 criterion 的相关段落后，模型不直接输出 final decision，而是先输出每个标准的独立判断。这类 decomposition / criterion-wise screening 是 systematic review automation 中较常见的设计：它把一个复杂排纳决策拆成多个可审计的子判断，便于定位错误来源，也便于后续人工复核。

建议输出 schema 为：

```json
{
  "criterion_judgments": {
    "population": {
      "judgment": "yes | no | unclear | not_applicable",
      "confidence": 0.0,
      "evidence_spans": ["..."],
      "reason": "..."
    },
    "intervention": {
      "judgment": "yes | no | unclear | not_applicable",
      "confidence": 0.0,
      "evidence_spans": ["..."],
      "reason": "..."
    },
    "comparator": {
      "judgment": "yes | no | unclear | not_applicable",
      "confidence": 0.0,
      "evidence_spans": ["..."],
      "reason": "..."
    },
    "outcome": {
      "judgment": "yes | no | unclear | not_applicable",
      "confidence": 0.0,
      "evidence_spans": ["..."],
      "reason": "..."
    },
    "study_design": {
      "judgment": "yes | no | unclear | not_applicable",
      "confidence": 0.0,
      "evidence_spans": ["..."],
      "reason": "..."
    }
  }
}
```

Criterion-wise 输出之后，再由一个独立 aggregation step 生成 final decision：

```json
{
  "decision": "include | exclude | needs_review",
  "failed_criterion": "...",
  "main_reason": "...",
  "supporting_criteria": ["..."],
  "confidence": 0.0
}
```

这种设计的优势是 final decision 不完全依赖模型一次性判断，而是可以分析每个 criterion 的错误类型，例如 population 判断错误、study design 判断错误或 evidence span 不支持判断。

#### 4.2.3 Aggregation Rule

聚合规则采用保守策略：

```text
If any hard exclusion criterion is clearly satisfied:
  exclude

Else if any mandatory inclusion criterion is clearly not satisfied:
  exclude

Else if one or more critical criteria are unclear:
  needs_review / include_for_review

Else:
  include
```

在自动化安全性评估中，`needs_review` 和 `include_for_review` 统一计为 `include`，因为不确定样本不应被自动排除。

### 4.3 本实验实际比较的方法

本实验主要比较以下方法：

| Method | Description |
| --- | --- |
| Direct Criteria-aware LLM | 输入 question、PICO/PICOS、criteria 和候选文献内容，直接输出 final include/exclude、reason 和 evidence spans |
| Direct Criteria-aware LLM with full text | 在 direct baseline 中加入 full text / XML sections，测试全文信息是否提升 final decision |
| Criterion-wise Evidence-grounded LLM | 先为每个 criterion 选择相关 evidence，再输出 criterion-level judgments，最后聚合 final decision |
| Conservative Two-stage Pipeline | Stage 1 用 abstract screening；Stage 2 用 criterion-wise full-text screening；unclear 样本进入 needs_review/include_for_review |

## 5. 实验一：Q2CRBench-3 Abstract Screening

### 5.1 目标

验证 LLM 是否能够基于 title/abstract + PICO/PICOS + criteria 安全完成初筛。

### 5.2 Dataset

```text
Q2CRBench-3:
- review question and PICO/PICOS
- candidate records with title / abstract
- gold include / exclude labels
```

### 5.3 Input

```text
Question
PICO / PICOS
Study design requirement
Inclusion criteria
Exclusion criteria
Title
Abstract
```

### 5.4 Output

```text
include / exclude
reason
criterion judgments
evidence spans
```

### 5.5 Methods

| Method | Description |
| --- | --- |
| Direct Criteria-aware LLM | 基于 title/abstract 直接输出 final include/exclude、reason 和 evidence spans |
| Criterion-wise LLM | 基于 title/abstract 分别判断 population、intervention、comparator、outcome、study design，再聚合 final decision |
| Conservative Abstract Screening | 基于 criterion-wise 判断进行保守聚合；不确定样本 pass_to_full_text，而不是自动 exclude |

### 5.6 Metrics

| Metric | Purpose |
| --- | --- |
| Sensitivity / recall for included studies | 判断是否漏掉应纳入研究 |
| False negative count | 衡量自动排除风险 |
| Specificity | 衡量排除无关文献能力 |
| Precision | 衡量 include pool 纯度 |
| Balanced accuracy | 综合衡量正负类表现 |
| High-confidence false negatives | 捕捉最危险的自动排除错误 |

### 5.7 Automation Criterion

Stage 1 若要进入可自动初筛状态，应满足：

```text
Sensitivity >= 0.98
High-confidence false negative = 0
```

如果无法达到该标准，则 abstract screening 更适合作为人工筛选辅助，而不适合直接自动排除。

## 6. 实验二：Q2CRBench-3 Full-text Screening

### 6.1 目标

验证 full text / XML sections 是否能让 LLM 获得更接近 final eligibility 的判断能力。

### 6.2 Dataset

```text
Q2CRBench-3:
- review question and PICO/PICOS
- screened-in or full-text-assessed candidate studies
- paper-level evidence profile or available full-text evidence
- gold final eligibility labels
```

### 6.3 Input

```text
Question
PICO / PICOS
Study design requirement
Inclusion criteria
Exclusion criteria
XML-sectioned full text
```

### 6.4 Output

```text
include / exclude
reason
criterion-level judgments
evidence spans
```

### 6.5 Methods

| Method | Description |
| --- | --- |
| Direct Criteria-aware LLM with full text | 直接输入可用 full text / XML sections，输出 final include/exclude |
| Criterion-wise Evidence-grounded LLM | 对每个 criterion 选择相关 evidence candidates，再逐项判断 |
| Conservative Criterion-wise LLM | criterion-wise 判断 + 保守聚合；关键证据不充分时输出 needs_review/include_for_review |

### 6.6 Metrics

```text
Sensitivity
Specificity
Precision
Balanced accuracy
Macro F1
False negative count
Reason support rate
High-confidence false negatives
```

### 6.7 Automation Criterion

Full-text screening 若要接近自动化，应至少满足：

```text
Sensitivity >= 0.95
Balanced accuracy >= 0.80
Unsupported exclusion reason <= 5%
High-confidence false negative = 0
```

更严格版本为：

```text
Sensitivity >= 0.98
High-confidence false negative = 0
```

## 7. 实验三：CSMeD-FT Final Screening

### 7.1 目标

验证 LLM 在 systematic review full-text screening 上的泛化能力，尤其关注 final include/exclude、exclusion reason 和 evidence support。

### 7.2 Dataset

```text
CSMeD-FT train / dev / test
```

### 7.3 Input Settings

| Setting | Input |
| --- | --- |
| Abstract-only | review metadata + criteria + title + abstract |
| Full-text XML | review metadata + criteria + XML sections |
| Abstract + full-text XML | review metadata + criteria + title + abstract + XML sections |

### 7.4 Methods

| Method | Description |
| --- | --- |
| Direct Criteria-aware LLM | strong baseline |
| Direct Criteria-aware LLM with full text | full-text baseline |
| Criterion-wise Evidence-grounded LLM | main method |

### 7.5 Metrics

```text
Included recall
False negative count
Specificity
Precision
Balanced accuracy
Macro F1
Reason accuracy
Reason support rate
High-confidence false negatives
```

CSMeD-FT 是 full-text publication screening benchmark，因此它适合作为 final include/exclude 能力的主验证集。

## 8. 实验四：One-step vs Two-stage Pipeline

### 8.1 目标

验证是否应将自动排纳系统设计为 abstract 初筛 + full-text 精筛的两阶段结构。

### 8.2 System Comparison

| System | Description |
| --- | --- |
| Abstract-only one-step | title/abstract 直接输出 final include/exclude |
| Full-text one-step | full text / XML sections 直接输出 final include/exclude |
| Two-stage pipeline | abstract screening 后，对 pass 的文献做 full-text screening |

### 8.3 Two-stage Decision Rule

```text
If Stage 1 = exclude:
  final = exclude

If Stage 1 = pass_to_full_text:
  final = Stage 2 decision
```

保守版本：

```text
If Stage 1 uncertain:
  pass_to_full_text

If Stage 2 uncertain:
  include / needs_review
```

实验评测时，`needs_review` 计为 `include`，以模拟安全排纳策略。

### 8.4 Metrics

| Metric | Meaning |
| --- | --- |
| End-to-end sensitivity | 整体是否漏掉应纳入研究 |
| End-to-end false negatives | 最关键的自动化风险 |
| End-to-end precision | 最终 include 的纯度 |
| Balanced accuracy | 综合表现 |
| Full-text workload reduction | 节省多少全文处理工作量 |
| Reason support rate | 排除理由是否有证据支持 |
| High-confidence false negatives | 是否存在危险自动排除 |

### 8.5 Decision Criterion

Two-stage pipeline 如果满足以下条件，则说明它比单阶段系统更实用：

```text
End-to-end sensitivity 接近 full-text one-step
Full-text workload 明显下降
High-confidence false negative = 0
Reason support rate 不下降
```

## 9. 实验五：Reason Generation 评测

### 9.1 目标

评估 LLM 不仅是否能输出 include/exclude，还能否给出准确、可审计、有证据支持的排除理由。

### 9.2 Reason Taxonomy

将预测 reason 和 gold reason 映射到统一类别：

```text
wrong_population
wrong_intervention
wrong_comparator
wrong_outcome
wrong_study_design
wrong_publication_type
not_primary_study
protocol_only
conference_abstract_only
duplicate_or_secondary_report
insufficient_data
indirect_evidence
other
```

### 9.3 Metrics

```text
Reason category accuracy
Reason macro F1
Evidence support rate
Unsupported reason rate
Hallucinated reason rate
```

### 9.4 Human Evaluation

从每个 benchmark 抽样：

```text
100 included cases
100 excluded cases
All high-confidence false negatives
All unsupported exclusion cases
```

人工判断以下内容：

```text
decision 是否合理
reason 是否正确
evidence span 是否支持 reason
是否属于可接受自动排除
```

## 10. Evaluation Metrics 定义

### 10.1 Decision Metrics

设 gold label 中 include 为正类，exclude 为负类。

```text
Sensitivity / Recall = TP / (TP + FN)
Specificity = TN / (TN + FP)
Precision = TP / (TP + FP)
Balanced accuracy = (Sensitivity + Specificity) / 2
Macro F1 = average(F1_include, F1_exclude)
False negative count = number of gold include cases predicted as exclude
```

### 10.2 Safety Metrics

```text
High-confidence false negative:
  gold = include
  prediction = exclude
  confidence >= predefined threshold

Unsupported exclusion reason:
  prediction = exclude
  but evidence span does not support the exclusion reason

Hallucinated reason:
  prediction gives a reason that is not supported by title/abstract/full text
```

建议 confidence threshold 设为：

```text
confidence >= 0.8
```

如不同模型的 confidence 不可比，可使用模型自评 confidence 结合人工抽样分析，而不作为唯一安全标准。

### 10.3 Workload Metric

Full-text workload reduction 用于衡量两阶段系统节省了多少全文筛选工作：

```text
Full-text workload = number of records passed to Stage 2 / total records

Full-text workload reduction = 1 - Full-text workload
```

## 11. 结果报告表格模板

### Table 1. Q2CRBench-3 Abstract Screening

| Method | Sensitivity | FN | Specificity | Precision | Balanced Acc | High-conf FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Direct Criteria-aware LLM |  |  |  |  |  |  |
| Criterion-wise LLM |  |  |  |  |  |  |
| Conservative Abstract Screening |  |  |  |  |  |  |

### Table 2. Q2CRBench-3 Full-text Screening

| Method | Sensitivity | FN | Specificity | Precision | Balanced Acc | Reason support |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Direct Criteria-aware LLM with full text |  |  |  |  |  |  |
| Criterion-wise Evidence-grounded LLM |  |  |  |  |  |  |
| Conservative Criterion-wise LLM |  |  |  |  |  |  |

### Table 3. CSMeD-FT Final Screening

| Input | Method | Sensitivity | FN | Specificity | Precision | Macro F1 | Reason Acc |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Abstract-only | Direct Criteria-aware LLM |  |  |  |  |  |  |
| Full-text / XML | Direct Criteria-aware LLM with full text |  |  |  |  |  |  |
| Full-text / XML | Criterion-wise Evidence-grounded LLM |  |  |  |  |  |  |

### Table 4. One-step vs Two-stage

| System | End-to-end Sensitivity | FN | Precision | Balanced Acc | Full-text workload | High-conf FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Abstract-only one-step |  |  |  |  | 0% |  |
| Full-text one-step |  |  |  |  | 100% |  |
| Two-stage pipeline |  |  |  |  |  |  |

### Table 5. Reason Quality

| Method | Reason Acc | Reason macro F1 | Evidence support | Unsupported reason | Hallucinated reason |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct Criteria-aware LLM |  |  |  |  |  |
| Criterion-wise Evidence-grounded LLM |  |  |  |  |  |
| Conservative Criterion-wise LLM |  |  |  |  |  |
