# 如何分析一篇文章的 `risk_of_bias`

> 基于 **Cochrane Handbook for Systematic Reviews of Interventions, Chapter 8: Assessing risk of bias in included studies**。本指南主要适用于随机对照试验（RCT），尤其是平行组试验。非随机研究、诊断试验、cluster-randomized、cross-over 等特殊设计需要在 `Other bias` 中补充设计特异性问题，必要时使用对应的专门工具。

---

## 1. 目标

阅读一篇研究文章、protocol、trial registry、补充材料或系统综述中的 study characteristics，输出一个结构化的 `risk_of_bias` 数组：

```json
{
  "risk_of_bias": [
    {
      "domain": "Random sequence generation (selection bias)",
      "judgement": "Low risk",
      "support_text": "Individually randomised and stratified by physician – random permuted blocks of 10 constructed using random number table (by research assistant not involved in recruitment)",
      "source": "source_review_characteristics"
    }
  ]
}
```

每个条目必须回答三个问题：

1. **这个 domain 在评估什么偏倚？**
2. **文章提供了什么证据？**
3. **这些证据支持 Low / High / Unclear 哪一种判断？**

---

## 2. 核心原则

### 2.1 评估的是 bias risk，不是论文质量

`risk_of_bias` 关注研究结果是否可能因为设计、执行、测量、分析或报告方式而系统性偏离真实干预效果。不要把伦理审批、样本量计算、写作规范、CONSORT 报告完整性等直接当作 risk of bias，除非它们具体影响了内部效度。

### 2.2 不要给总分

不要使用“总分”“平均分”“Jadad score”等方式合并所有 domain。每个 domain 独立判断；总结时只按关键 outcome 讨论哪些 domain 最影响结论。

### 2.3 每个 judgement 都必须有 support

`support_text` 不能只写 “low risk” 或 “randomized”。它必须包含：

- 文章中的原文摘录，或对原文事实的准确总结；
- 信息来源，例如 article methods、protocol、registry、review characteristics、author correspondence；
- 判断理由，例如 “random number table = random component, therefore low risk”。

### 2.4 `Unclear risk` 不是中等风险

`Unclear risk` 表示：信息不足、描述不够细、该 outcome 未测量，或虽然知道做法但无法判断它是否会造成实质性偏倚。不要在没有证据时猜测为 Low 或 High。

---

## 3. 标准输出 schema

建议固定使用下面字段：

```json
{
  "risk_of_bias": [
    {
      "domain": "string, 必须使用标准 domain 名称",
      "judgement": "Low risk | High risk | Unclear risk",
      "support_text": "string, 证据 + 推理 + 必要时说明 outcome 范围",
      "source": "string, 信息来源"
    }
  ]
}
```

可选增强字段：

```json
{
  "risk_of_bias": [
    {
      "domain": "Blinding of outcome assessment (detection bias)",
      "judgement": "Low risk",
      "support_text": "Consultations were audiotaped, transcribed and coded by two coders blinded to group allocation; this supports low detection bias for transcript-coded outcomes.",
      "source": "article_methods_page_716",
      "outcome_scope": "transcript-coded consultation outcomes",
      "quote": "Two coders were trained and blinded to group allocation.",
      "rationale": "Outcome assessors were blinded and the blinding was unlikely to be broken for coded transcripts."
    }
  ]
}
```

---

## 4. 标准 domains 与判断规则

### 4.1 Random sequence generation（selection bias）

**问题：分组序列是不是随机产生的？**

| Judgement | 判断依据 |
|---|---|
| Low risk | 明确使用随机成分：random number table、computer random number generator、coin tossing、shuffling cards/envelopes、throwing dice、drawing lots、minimization 等。 |
| High risk | 使用非随机规则：出生日期奇偶、入院日期、病历号、轮替、医生判断、患者偏好、实验室结果、干预可得性等。 |
| Unclear risk | 只写 “randomized” / “randomly allocated”，但没有说明序列如何生成；或只说 block randomization 但没有说明 block 如何随机产生。 |

**写法示例：**

```json
{
  "domain": "Random sequence generation (selection bias)",
  "judgement": "Low risk",
  "support_text": "The study reports individual randomisation, stratified by physician, using random permuted blocks of 10 constructed from a random number table by a research assistant not involved in recruitment. This includes a random component and supports comparable groups.",
  "source": "source_review_characteristics"
}
```

---

### 4.2 Allocation concealment（selection bias）

**问题：招募/分配前，研究人员能不能预知下一个受试者会被分到哪组？**

| Judgement | 判断依据 |
|---|---|
| Low risk | 中央随机、电话/网页/药房控制随机、外观一致的连续编号药盒、连续编号不透明密封信封（SNOSE）等。 |
| High risk | 开放随机表、未密封/透明/非连续编号信封、轮替、出生日期、病历号、任何明显未隐藏的分配方式。 |
| Unclear risk | 说用了信封，但未说明是否连续编号、不透明、密封；或完全没有描述 concealment。 |

**注意：** allocation concealment 发生在分配前；blinding 发生在分配后。不要混淆。

**写法示例：**

```json
{
  "domain": "Allocation concealment (selection bias)",
  "judgement": "Low risk",
  "support_text": "Allocations were concealed using sequentially numbered, opaque, sealed envelopes, so recruiters were unlikely to foresee assignments before enrolment.",
  "source": "source_review_characteristics"
}
```

---

### 4.3 Blinding of participants and personnel（performance bias）

**问题：参与者和执行干预的人是否知道分组？如果知道，会不会影响实际护理、共同干预、行为或结局？**

| Judgement | 判断依据 |
|---|---|
| Low risk | 已有效盲法，且不太可能破盲；或虽未盲法，但该 outcome 不太可能受知晓分组影响。 |
| High risk | 未盲法/盲法不完整，且 outcome 很可能受影响；或尝试盲法但很可能破盲，并且 outcome 易受影响。 |
| Unclear risk | 信息不足；不知道谁被盲；或无法判断缺乏盲法对该 outcome 的影响。 |

**必须按 outcome 或 outcome group 判断。** 例如：

- 客观 outcome（如 all-cause mortality）可能受影响较小；
- 主观 outcome（如 pain、satisfaction、anxiety、自报量表）可能受影响较大；
- 行为/沟通类 outcome 可能特别容易受到医生或患者知道分组的影响。

**写法示例：**

```json
{
  "domain": "Blinding of participants and personnel (performance bias)",
  "judgement": "Unclear risk",
  "support_text": "Physicians were unblinded, and it is unclear whether patients or carers were blinded. Because professional endorsement of the QPL may influence consultation behaviour, the likely impact on communication outcomes cannot be determined from the available information.",
  "source": "source_review_characteristics"
}
```

---

### 4.4 Blinding of outcome assessment（detection bias）

**问题：测量或判定 outcome 的人是否知道分组？如果知道，会不会影响 outcome measurement？**

| Judgement | 判断依据 |
|---|---|
| Low risk | outcome assessor 被盲，且不太可能破盲；或未盲但 outcome measurement 不太可能受影响。 |
| High risk | outcome assessor 未盲，且 outcome measurement 很可能受影响；或盲法可能破坏且 outcome 易受影响。 |
| Unclear risk | 信息不足；不知道谁评估 outcome；或研究未测量该 outcome。 |

**注意：** 如果 outcome 是患者自报，而患者知道分组，患者本人就是 outcome assessor；不能只看研究人员是否 blinded。

**写法示例：**

```json
{
  "domain": "Blinding of outcome assessment (detection bias)",
  "judgement": "Low risk",
  "support_text": "Consultations were audiotaped, transcribed and analysed by coders blinded to group allocation; one coder coded all transcripts and recoded 10%, and a second blinded coder coded 10% for inter-rater reliability. This supports low detection bias for transcript-coded outcomes.",
  "source": "source_review_characteristics"
}
```

---

### 4.5 Incomplete outcome data（attrition bias）

**问题：缺失数据、退出、排除或分析方式是否可能系统性改变效果估计？**

| Judgement | 判断依据 |
|---|---|
| Low risk | 无缺失；缺失原因与真实 outcome 不太相关；两组缺失数量和原因平衡；缺失比例不足以实质性影响效果；使用了合适的缺失数据处理方法。 |
| High risk | 缺失原因可能与真实 outcome 相关，且两组数量或原因不平衡；缺失比例足以改变效果；明显 as-treated/per-protocol 分析且偏离随机分组严重；简单插补方法不合适。 |
| Unclear risk | 随机人数、缺失人数或缺失原因报告不足；无法判断缺失对 outcome 的影响。 |

判断时不要只看“缺失比例高不高”，还要看：

1. 每组缺失人数；
2. 缺失原因；
3. 缺失是否与 outcome 相关；
4. 缺失对效应量的潜在影响；
5. 是否按随机分组分析。

**写法示例：**

```json
{
  "domain": "Incomplete outcome data (attrition bias)",
  "judgement": "Low risk",
  "support_text": "Loss to follow-up was low, 4/174 overall, and balanced across groups with 2 participants missing in each group and comparable reasons. This is unlikely to materially affect the results.",
  "source": "source_review_characteristics"
}
```

---

### 4.6 Selective reporting（reporting bias）

**问题：研究是否选择性报告了有利或显著的 outcome、时间点、量表、亚组或分析方式？**

| Judgement | 判断依据 |
|---|---|
| Low risk | protocol/registry 可得，且所有预设的 primary/secondary outcomes 以预设方式报告；或虽无 protocol，但文章明显报告了所有预期 outcome。 |
| High risk | 预设 primary outcome 未报告；primary outcome 使用未预设的测量、分析或子集；报告了未预设 primary outcome 且无合理解释；review 关心的 outcome 报告不完整，无法进入 meta-analysis；关键 outcome 缺失。 |
| Unclear risk | 无 protocol/registry，且信息不足以确认是否选择性报告。很多研究会落入这一类。 |

**检查顺序：**

1. 找 trial registry / protocol / SAP；
2. 对比 protocol 的 outcomes 与文章 Results；
3. 对比 Methods 中说测了什么与 Results 中报告了什么；
4. 检查是否只写 “not significant” 但不给数据；
5. 检查是否选择了某个时间点、某个量表、某个 subscale 或某个 subgroup。

**写法示例：**

```json
{
  "domain": "Selective reporting (reporting bias)",
  "judgement": "Unclear risk",
  "support_text": "No trial protocol or registry record was available in the extracted materials, and the available report does not provide enough information to confirm that all prespecified outcomes were reported as planned.",
  "source": "article_methods_and_results"
}
```

---

### 4.7 Other bias (不评估)

**问题：是否存在上述 domains 没覆盖、但可能直接造成内部偏倚的问题？**

| Judgement | 判断依据 |
|---|---|
| Low risk | 未发现其他可能直接影响内部效度的偏倚来源。 |
| High risk | 存在重要偏倚风险，例如设计特异性问题、严重 baseline imbalance、contamination、不恰当共同干预、interim result 影响招募、欺诈嫌疑等。 |
| Unclear risk | 可能有问题，但信息不足；或无法说明该问题会造成重要偏倚。 |

**不要放进 Other bias 的内容：**

- 单纯样本量小（这是 imprecision，不是 bias）；
- 单纯没有伦理审批说明；
- 单纯报告格式不佳；
- 单纯外部适用性问题；
- 已经被前面 domain 覆盖的问题，例如缺失数据不要重复放到 Other bias。

**写法示例：**

```json
{
  "domain": "Other bias",
  "judgement": "Low risk",
  "support_text": "No obvious baseline imbalance, contamination, design-specific problem, or other direct threat to internal validity was identified from the available study characteristics.",
  "source": "article_methods_and_characteristics"
}
```

---

## 5. 实际分析流程

### Step 1：确认研究设计

先判断文章是否是：

- individually randomized parallel-group RCT；
- cluster-randomized trial；
- cross-over trial；
- quasi-randomized trial；
- non-randomized study；
- pilot/feasibility study；
- qualitative study。

如果不是标准 RCT，需要在 `Other bias` 或专门工具中处理设计特异性偏倚。

### Step 2：列出关键 outcomes

至少区分：

- 主观 vs 客观；
- 患者自报 vs 研究者测量；
- 短期 vs 长期；
- 主要 outcome vs 次要 outcome。

Blinding 和 incomplete outcome data 通常需要按 outcome 或 outcome group 分开判断。

### Step 3：逐 domain 抽取证据

优先查找：

1. Methods：randomization、allocation、masking/blinding、outcome measurement、statistical analysis；
2. Results：participant flow、loss to follow-up、baseline table、reported outcomes；
3. Protocol / registry / SAP：预设 outcome 和分析计划；
4. Supplement / appendix；
5. Review characteristics 或作者通信。

### Step 4：先写 support，再给 judgement

推荐顺序：

1. 写出找到的事实；
2. 写出事实为什么支持某个判断；
3. 再填 `judgement`。

不要先决定 Low/High，再倒推理由。

### Step 5：使用固定判断词

只允许：

- `Low risk`
- `High risk`
- `Unclear risk`

不要输出 “moderate risk”、“some concerns”、“probably low” 等非本模板词汇。可以把 “probably done / probably not done” 写在 `support_text` 中，但 `judgement` 仍然必须是三选一。

---

## 6. 常见错误

| 错误 | 正确做法 |
|---|---|
| 把 “randomized” 直接判为 Low risk | 必须看随机序列如何产生；只有笼统写 randomized 通常是 Unclear risk。 |
| 把 allocation concealment 和 blinding 混为一谈 | allocation concealment 是分配前防止预知分组；blinding 是分配后防止知晓分组影响行为或测量。 |
| 用缺失比例一个数字直接判断 attrition bias | 要同时看缺失人数、两组是否平衡、缺失原因、是否与 outcome 有关、处理方法是否合适。 |
| 所有 blinding 都给同一个 judgement | blinding 要按 outcome 判断。主观 outcome 和客观 outcome 的风险可能不同。 |
| `support_text` 只写 “adequate” | 必须写清楚具体证据：谁、做了什么、在哪里报告、为什么支持判断。 |
| funding source 直接判 High risk | funding 应记录在 characteristics；只有当它具体影响设计、分析、报告并导致内部偏倚时，才作为 RoB 问题。 |

---

## 7. 可直接使用的 Prompt 模板

```text
你是系统综述方法学助手。请根据 Cochrane Handbook Chapter 8 的 Risk of Bias 思路，分析下面这篇研究文章/研究特征记录。

任务：
1. 只评估内部偏倚风险，不评估写作质量、伦理质量或外部适用性。
2. 对以下 domains 分别判断：
   - Random sequence generation (selection bias)
   - Allocation concealment (selection bias)
   - Blinding of participants and personnel (performance bias)
   - Blinding of outcome assessment (detection bias)
   - Incomplete outcome data (attrition bias)
   - Selective reporting (reporting bias)
   - Other bias
3. 每个 judgement 只能是：Low risk / High risk / Unclear risk。
4. 每个 support_text 必须包含具体证据和判断理由；证据不足时写清楚为什么不足，并判 Unclear risk。
5. 对 blinding 和 incomplete outcome data，如不同 outcome 风险不同，请在 domain 名称或 support_text 中说明 outcome_scope。
6. 不要计算总分，不要输出平均风险等级。

输出 JSON：
{
  "risk_of_bias": [
    {
      "domain": "...",
      "judgement": "Low risk | High risk | Unclear risk",
      "support_text": "证据 + 判断理由",
      "source": "article_methods | article_results | protocol | trial_registry | supplement | author_correspondence | source_review_characteristics"
    }
  ]
}

输入材料：
[在这里粘贴文章全文、研究特征、protocol 或 registry 信息]
```

---

## 8. 完整输出示例

```json
{
  "risk_of_bias": [
    {
      "domain": "Random sequence generation (selection bias)",
      "judgement": "Low risk",
      "support_text": "Individually randomised and stratified by physician; random permuted blocks of 10 were constructed using a random number table by a research assistant not involved in recruitment. This includes a random component and supports comparable groups.",
      "source": "source_review_characteristics"
    },
    {
      "domain": "Allocation concealment (selection bias)",
      "judgement": "Low risk",
      "support_text": "Allocations were concealed using sequentially numbered, opaque, sealed envelopes, so the next assignment was unlikely to be foreseen before enrolment.",
      "source": "source_review_characteristics"
    },
    {
      "domain": "Blinding of participants and personnel (performance bias)",
      "judgement": "Unclear risk",
      "support_text": "Physicians were unblinded, and it is unclear whether patients and carers were blinded. Because professional endorsement of the QPL may affect consultation behaviour, the impact on outcomes cannot be determined from the available information.",
      "source": "source_review_characteristics"
    },
    {
      "domain": "Blinding of outcome assessment (detection bias)",
      "judgement": "Low risk",
      "support_text": "Consultations were audiotaped, transcribed and analysed by coders blinded to group allocation. This supports low detection bias for transcript-coded consultation outcomes.",
      "source": "source_review_characteristics"
    },
    {
      "domain": "Incomplete outcome data (attrition bias)",
      "judgement": "Low risk",
      "support_text": "Loss to follow-up was low, 4/174 overall, balanced across groups with 2 missing in each group and comparable reasons. This is unlikely to materially affect the results.",
      "source": "source_review_characteristics"
    },
    {
      "domain": "Selective reporting (reporting bias)",
      "judgement": "Unclear risk",
      "support_text": "No protocol or trial registry information was available in the extracted material, so it is not possible to confirm whether all prespecified outcomes were reported as planned.",
      "source": "article_methods_and_results"
    },
    {
      "domain": "Other bias",
      "judgement": "Unclear risk",
      "support_text": "The available extracted material does not provide enough information to rule out all other potential sources of bias, such as design-specific issues, contamination, or unexplained baseline imbalance.",
      "source": "article_methods_and_results"
    }
  ]
}
```

---

## 9. 最终检查清单

提交前逐项检查：

- [ ] 是否覆盖 7 个标准 domains？
- [ ] judgement 是否只使用 `Low risk` / `High risk` / `Unclear risk`？
- [ ] 每个条目是否都有具体 `support_text`？
- [ ] `support_text` 是否说明了信息来源？
- [ ] 是否避免了总分或平均分？
- [ ] blinding 是否按 outcome 或 outcome group 考虑？
- [ ] incomplete outcome data 是否看了缺失原因、平衡性和潜在影响？
- [ ] selective reporting 是否查了 protocol/registry 或 Methods vs Results？
- [ ] Other bias 是否只包含可能直接导致内部偏倚的问题？
```
