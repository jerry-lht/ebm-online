# Risk of Bias 通用分析指南

> 适用对象：需要从一篇临床研究文章、研究方案、注册记录、补充材料或系统综述的 `Characteristics of included studies` 中抽取并判断 `risk_of_bias` 的场景。  
> 核心目标：不是给文章“打质量分”，而是判断研究的设计、实施、分析和报告是否可能让干预效果估计发生系统性偏差。

---

## 1. 输出格式

推荐统一输出为：

```json
{
  "risk_of_bias": [
    {
      "domain": "Random sequence generation (selection bias)",
      "judgement": "Low risk | High risk | Unclear risk",
      "support_text": "Quote: ... Comment: ...",
      "source": "source_full_text | source_protocol | source_registry | source_review_characteristics | author_correspondence"
    }
  ]
}
```

字段说明：

| 字段 | 含义 | 写法要求 |
|---|---|---|
| `domain` | 偏倚领域 | 使用标准 domain 名称，必要时加 outcome/time point |
| `judgement` | 风险判断 | 只用 `Low risk`、`High risk`、`Unclear risk` |
| `support_text` | 支持判断的证据和解释 | 先写原文或摘要证据，再写为什么这样判断 |
| `source` | 信息来源 | 标明来自全文、方案、注册、系统综述特征表或作者通信 |

可选扩展字段：

```json
{
  "outcome_or_class": "subjective outcomes / objective outcomes / 3-week follow-up",
  "quote": "原文证据",
  "rationale": "判断逻辑",
  "page_or_section": "Methods, p.716",
  "notes": "需要复核的问题"
}
```

---

## 2. 总体工作流

### Step 1：先识别研究类型

先判断文章属于哪类研究设计：

- 个体随机平行组 RCT
- cluster-randomized trial
- cross-over trial
- 多臂试验
- 非随机研究
- 混合设计或不清楚设计

本指南默认以随机试验为主。如果是 cluster、cross-over、多臂或非随机研究，需要在 `Other bias` 或额外 domain 中补充设计特异性风险。

---

### Step 2：收集所有可用证据

不要只看摘要。按优先级查看：

1. 研究方案或注册记录
2. 正文 Methods
3. CONSORT flow diagram / Results 中的失访和排除信息
4. Tables，包括基线表和 outcome 表
5. Supplementary appendix
6. 系统综述中的 `Characteristics of included studies`
7. 作者通信或澄清信息

如果输入数据是结构化 JSON，可按下面映射找证据：

| 结构化字段 | 优先用于判断 |
|---|---|
| `random_sequence_generation` | Random sequence generation |
| `allocation_concealment` | Allocation concealment |
| `masking` / `blinding` | Blinding of participants/personnel；Blinding of outcome assessment |
| `missing_data_methods`、失访人数、排除理由 | Incomplete outcome data |
| `outcomes`、protocol/registry、reported outcomes | Selective reporting |
| `study_design`、`unit_of_analysis`、`centres` | Other bias 或设计特异性偏倚 |
| `funding_support`、`conflicts_of_interest` | 通常记录为研究特征；只有存在直接影响机制时才放进 RoB |

---

### Step 3：按 domain 判断，而不是按关键词判断

判断时采用固定逻辑：

```text
证据是什么？
→ 这条证据说明了研究实际怎么做？
→ 这种做法是否可能造成系统性偏倚？
→ 偏倚是否足以影响结果或结论？
→ Low / High / Unclear
```

注意：

- “randomized” 这个词本身不足以判断为 `Low risk`。
- “double blind” 这个词本身不足以说明谁被盲、盲法是否成功。
- “intention-to-treat” 这个词本身不足以说明没有 attrition bias。
- 没有信息通常是 `Unclear risk`，不是 `Low risk`。
- RoB 是内部效度判断，不是样本量、伦理审批、写作规范或外部适用性的评分。

---

## 3. 七个标准 domain 的通用判断规则

## 3.1 Random sequence generation (selection bias)

### 评估问题

研究是否使用了真正随机的分配序列？

### Low risk

有明确随机成分，例如：

- random number table
- computer random number generator
- coin tossing
- shuffled cards/envelopes
- dice
- drawing lots
- minimization
- random permuted blocks，并说明随机生成方式

### High risk

使用非随机或可预测规则，例如：

- 出生日期奇偶
- 入院日期或星期
- 病历号
- 交替分配
- 医生判断
- 患者偏好
- 检测结果
- 干预可获得性

### Unclear risk

- 只说 “randomized” 或 “randomly allocated”，未说明方法
- 只说 blocked / stratified randomization，但未说明随机序列如何产生
- 信息不足，无法判断是否真正随机

### 推荐 support_text 写法

```text
Quote: "Patients were randomly allocated."
Comment: The method used to generate the allocation sequence was not described; therefore the risk is unclear.
```

---

## 3.2 Allocation concealment (selection bias)

### 评估问题

在纳入患者之前，招募者是否无法预知下一个分配结果？

这与 blinding 不同。Allocation concealment 发生在分配之前；blinding 发生在分配之后。

### Low risk

可防止预知分配，例如：

- central allocation
- telephone/web/pharmacy-controlled randomization
- sequentially numbered identical drug containers
- sequentially numbered, opaque, sealed envelopes, 即 SNOSE

### High risk

分配可能被预知，例如：

- 公开随机列表
- 信封未密封、非不透明、未连续编号
- 交替分配
- 按出生日期、入院日期、病历号
- 任何明确未隐藏的程序

### Unclear risk

- 只说使用 envelopes，但没说明是否 sequentially numbered、opaque、sealed
- 没有说明 concealment 方法

### 推荐 support_text 写法

```text
Quote: "Allocation was performed using sealed envelopes."
Comment: It is unclear whether envelopes were sequentially numbered and opaque; allocation concealment cannot be judged as adequate.
```

---

## 3.3 Blinding of participants and personnel (performance bias)

### 评估问题

参与者和实施干预的人员是否知道分组？如果知道，是否可能影响实际照护、行为、共同干预或结局？

这个 domain 通常要按 outcome 或 outcome class 判断，例如：

- subjective outcomes
- objective outcomes
- patient-reported outcomes
- clinician-assessed outcomes

### Low risk

满足任一情况：

- 参与者和关键人员成功盲法，且不太可能破盲
- 未盲或盲法不完整，但该 outcome 不太可能受知晓分组影响

例如死亡率通常比疼痛评分更不容易受 performance bias 影响。

### High risk

满足任一情况：

- 未盲或盲法不完整，且 outcome 可能受知晓分组影响
- 尝试盲法但很可能破盲，且 outcome 可能受影响

### Unclear risk

- 没说谁被盲
- 只说 “double blind”，但未说明参与者、医生、护士、研究人员具体谁被盲
- 信息不足，无法判断对 outcome 的影响
- 研究没有测量该 outcome

### 推荐 support_text 写法

```text
Quote: "Physicians were aware of group allocation."
Comment: Participants' behavior and consultation content could plausibly be influenced by unblinded physicians; risk is high for subjective communication outcomes.
```

---

## 3.4 Blinding of outcome assessment (detection bias)

### 评估问题

测量或判定 outcome 的人是否知道分组？如果知道，是否可能影响 outcome measurement？

要先问：谁在评估 outcome？

- 患者自己填写问卷
- 医生判断
- 独立评估员
- blinded coder
- 实验室或影像系统
- 医疗记录抽取者

### Low risk

满足任一情况：

- outcome assessor 被盲，且不太可能破盲
- assessor 未盲，但 outcome measurement 不太可能受影响，例如客观死亡率

### High risk

满足任一情况：

- assessor 未盲，且 outcome 是主观或可被判断影响
- assessor 可能破盲，且 measurement 可能受影响

### Unclear risk

- 未说明 outcome assessor 是否盲
- 只说研究 double blind，但不清楚 outcome assessor 是否盲
- outcome 没有被研究测量

### 推荐 support_text 写法

```text
Quote: "Consultations were audiotaped, transcribed and analysed by coders blinded to group allocation."
Comment: Outcome assessment was conducted by blinded coders; risk of detection bias is low for coded consultation outcomes.
```

---

## 3.5 Incomplete outcome data (attrition bias)

### 评估问题

失访、退出、排除或缺失数据是否可能让结果偏倚？

要提取：

- 每组随机人数
- 每组纳入分析人数
- 每组缺失人数
- 缺失原因
- 缺失是否平衡
- 是否使用 ITT
- 是否有不恰当 imputation
- 是否是 as-treated / per-protocol analysis

### Low risk

满足任一情况：

- 没有 missing outcome data
- 缺失原因不太可能与真实 outcome 有关
- 两组缺失人数和原因相似
- 缺失比例相对于事件率或效应大小不足以造成重要偏倚
- 使用了合适的缺失数据处理方法

### High risk

满足任一情况：

- 缺失原因可能与真实 outcome 有关，且两组缺失人数或原因不平衡
- 缺失比例足以影响效应估计
- 因 “lack of efficacy” 或 adverse events 排除，且两组不平衡
- 使用 as-treated analysis，且实际接受干预与随机分配明显不一致
- 使用不恰当的简单插补，例如不合理的 LOCF 或把缺失者直接当作失败/成功

### Unclear risk

- 未报告每组失访人数
- 未报告缺失原因
- 只说 ITT，但没有说明缺失数据如何处理
- outcome 未测量

### 推荐 support_text 写法

```text
Quote: "Four of 174 participants were lost to follow-up, two in each group, with similar reasons."
Comment: Missing data were low and balanced across groups; attrition bias is unlikely.
```


## 4. 判断等级的通用原则

## Low risk

使用条件：

- 有足够信息说明方法能避免该类偏倚；或
- 即使方法不完美，也不太可能对该 outcome 造成实质性影响。

不要因为文章写得好就自动判 Low risk。

---

## High risk

使用条件：

- 有证据显示方法存在缺陷；且
- 该缺陷可能造成足以影响结果或结论的系统性偏倚。

不要因为信息缺失就直接判 High risk，除非缺失本身代表明显方法问题或有其他证据支持。

---

## Unclear risk

使用条件：

- 信息不足，无法判断 Low 或 High；或
- 知道发生了什么，但不清楚它是否会造成实质性偏倚；或
- 该 entry 对当前 outcome 不适用。

`Unclear risk` 不是“中等风险”，而是“不确定”。

---


## 6. 通用 prompt 模板

可以直接给模型或人工评估员使用：

```text
你是系统综述中的 risk of bias 评估员。请基于给定研究资料，按照 Cochrane Handbook Chapter 8 的 domain-based RoB 方法，评估每个 included study 的偏倚风险。

请遵守以下规则：
1. 只评估 risk of bias，不做整体质量打分，不使用总分。
2. 每个 domain 必须输出 judgement 和 support_text。
3. judgement 只能是：Low risk、High risk、Unclear risk。
4. support_text 必须包含证据和判断理由。优先使用 Quote + Comment 格式。
5. 如果信息不足，使用 Unclear risk，并明确说明缺少什么信息。
6. Blinding 和 incomplete outcome data 应按 outcome 或 outcome class 判断；如果不同 outcome 风险不同，不要合并成一个判断。
7. Selective reporting 要优先比较 protocol/registry 与 published report。
8. Other bias 只记录可能直接影响内部效度的问题，不要把样本量小、伦理审批、外部适用性差简单放进去。
9. 输出必须是 JSON，不要输出额外解释。

输入资料：
[粘贴 article full text / structured JSON / review characteristics / protocol / registry]

输出 schema：
{
  "risk_of_bias": [
    {
      "domain": "...",
      "judgement": "Low risk | High risk | Unclear risk",
      "support_text": "Quote: ... Comment: ...",
      "source": "..."
    }
  ]
}
```

---

## 7. 通用输出示例

```json
{
  "risk_of_bias": [
    {
      "domain": "Random sequence generation (selection bias)",
      "judgement": "Unclear risk",
      "support_text": "Quote: \"Participants were randomly assigned to intervention or control.\" Comment: The report states that allocation was random, but does not describe the sequence generation method; insufficient information to judge whether the sequence was truly random.",
      "source": "source_full_text_methods"
    },
    {
      "domain": "Allocation concealment (selection bias)",
      "judgement": "Low risk",
      "support_text": "Quote: \"Randomization was performed centrally by an independent trials unit using a web-based system.\" Comment: Recruiters could not foresee assignments before enrolment; allocation concealment was adequate.",
      "source": "source_full_text_methods"
    },
    {
      "domain": "Blinding of participants and personnel (performance bias): patient-reported outcomes",
      "judgement": "High risk",
      "support_text": "Quote: \"Participants and clinicians were not blinded because of the nature of the intervention.\" Comment: Patient-reported outcomes could plausibly be influenced by knowledge of group allocation.",
      "source": "source_full_text_methods"
    },
    {
      "domain": "Blinding of outcome assessment (detection bias): objective outcomes",
      "judgement": "Low risk",
      "support_text": "Summary: The outcome was all-cause mortality obtained from medical records. Comment: Outcome measurement is unlikely to be influenced by lack of assessor blinding.",
      "source": "source_full_text_results"
    },
    {
      "domain": "Incomplete outcome data (attrition bias): 3-month outcomes",
      "judgement": "Unclear risk",
      "support_text": "Summary: The report gives the number analysed but not the number randomized in each group or reasons for missing data. Comment: Insufficient information to assess whether missing outcome data could bias the result.",
      "source": "source_full_text_results"
    },
    {
      "domain": "Selective reporting (reporting bias)",
      "judgement": "Unclear risk",
      "support_text": "Summary: No protocol or trial registry entry was available. Comment: Reported outcomes appear consistent with the Methods section, but selective reporting cannot be excluded.",
      "source": "source_full_text_methods_results"
    },
    {
      "domain": "Other bias",
      "judgement": "Low risk",
      "support_text": "Summary: Baseline characteristics were broadly similar and no important design-specific source of bias was identified. Comment: The study appears free of other important sources of internal bias.",
      "source": "source_full_text_tables"
    }
  ]
}
```

---

## 8. 快速核对清单

在完成 RoB 前，逐项问：

- [ ] 研究分配序列是真随机的吗？
- [ ] 招募者在分配前能不能预知下一组？
- [ ] 参与者和实施人员是否知道分组？这会影响 outcome 吗？
- [ ] outcome assessor 是否知道分组？outcome 是否主观？
- [ ] 每组随机人数、分析人数、缺失人数和缺失原因是否清楚？
- [ ] 是否有 protocol/registry？预设 outcomes 是否全部报告？
- [ ] 是否存在设计特异性偏倚、严重基线不平衡、污染、错误分析或其他内部效度问题？
- [ ] 每个 judgement 是否都有 support_text？
- [ ] 是否把“不清楚”错误写成了“低风险”？
- [ ] 是否避免了总分、Jadad 分数或笼统“质量高/低”的说法？

---

## 9. 最重要的原则

Risk of bias 分析不是“看文章写得规范不规范”，而是回答：

> 如果这项研究的结果偏离真实干预效果，最可能是哪些设计、实施、测量、缺失数据或报告选择造成的？这些问题是否足以影响结果或结论？

每个 domain 都要做到：

```text
证据可追溯 + 判断可解释 + 不确定就明说不确定
```
