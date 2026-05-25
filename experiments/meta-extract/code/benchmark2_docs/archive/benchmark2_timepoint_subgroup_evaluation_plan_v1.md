# Benchmark2 中 `timepoint` / `subgroup` 评测方案（双主实验版）

## 1. 为什么正式评测放在 benchmark2

当前 `timepoint` 和 `subgroup` 不适合直接放在 benchmark1 做正式自由生成主评分，核心原因不是字段本身不重要，而是 benchmark1 的 review-level gold 只保留了 SR author 最终采用的分析结构，不覆盖文献中所有真实存在、且可能合理的 `subgroup` / `timepoint` 候选。

这会导致一个系统性问题：模型若完整地从 study 文本中提出更多真实存在的 `subgroup` 或 `timepoint`，在 benchmark1 上会因为超出 gold 而被误伤，尤其会严重影响 precision 的解释力。因此，benchmark1 更适合把这两个字段放在开放世界案例分析或辅助 error analysis 中，而不适合当作正式主评分字段。

benchmark2 更接近官方 analysis-item 层，定义更适合承载正式评测。其核心特征是：

- `comparison × subgroup` 定义 analysis item；
- `timepoints` 作为 item context 保留，而不是单独扩成 Cartesian product 维度；
- gold 更接近 official analysis setting / official data row routing 的中间层，而不是自由生成的 review-level candidate 列表。

因此，本方案将 `subgroup` 和 `timepoint` 的正式评测全部放在 benchmark2，并定义为两个**同等地位**的主实验：

- 实验一：`Official Item Support`
- 实验二：`Open-world Proposal`

两者都进入正式结果部分，但指标不同、解释口径不同，不能混成一个总分。

---

## 2. 总体设计原则

本方案采用以下固定前提：

- `subgroup` 和 `timepoint` 分开评分；
- `pair` 只作为结构指标并列汇报，不单独升格成第三个正式主实验；
- benchmark2 的正式评测对象是 study-level / analysis-item-level 能力，而不是 review-level 自由生成能力；
- `full-text` 作为主输入设置，`abstract-only` 作为对照设置；
- `relevant-passages` 可以进入扩展实验，但不作为首轮必跑设置。

---

## 3. 主实验一：Official Item Support

### 3.1 任务目标

给定官方 analysis-item 上下文，判断当前 study 是否支持其中的 `subgroup` 与 `timepoint`，并在支持时验证 grounding 是否准确。该实验测的是 closed-world 判别与 grounding 能力。

### 3.2 评测单元

输入单元固定为：

```text
(review, study, outcome_concept, comparison, subgroup, timepoints)
```

其中：

- `subgroup` 是 official item identity 的一部分；
- `timepoints` 是 official item context；
- 不再把 `timepoints` 展开成新的 item 维度。

### 3.3 输入

- `SR title`
- `SR PICO`
- 当前 study 的证据文本：
  - 主设置：`full-text`（无 full text 时退化为 abstract）
  - 对照设置：`abstract-only`
- official analysis-item context：
  - `outcome_concept`
  - `comparison`
  - `subgroup`
  - `timepoints`

### 3.4 输出

输出拆成两个并列子任务：

- `subgroup_support_status = supported | not_supported | uncertain`
- `timepoint_support_status = supported | not_supported | uncertain`

并增加条件化 grounding 输出：

```json
{
  "subgroup_support_status": "supported | not_supported | uncertain",
  "timepoint_support_status": "supported | not_supported | uncertain",
  "subgroup_grounded_value": "...",
  "timepoint_grounded_values": ["..."]
}
```

其中：

- 仅当 `subgroup_support_status = supported` 时填写 `subgroup_grounded_value`
- 仅当 `timepoint_support_status = supported` 时填写 `timepoint_grounded_values`

### 3.5 gold 构造

gold 直接来自 benchmark2 的 `analysis_items`：

- official `subgroup`
- official `timepoints`

构造时采用以下规则：

- `subgroup` 保持 analysis-item identity 组成部分的地位；
- `timepoints` 作为 item context 原样保留；
- 不将 `timepoints` 扩成新的 item 维度；
- 同一 `(review, study, outcome_concept, comparison, subgroup, timepoints)` 构成一个评测实例。

### 3.6 负样本构造

为了让该实验真正测“判别”能力，负样本构造必须写死，不能临场自由发挥。首轮建议使用三类难负样本：

1. 同一 review 内其他 official subgroup/timepoint item
2. 同一 comparison 下的相邻时间窗
3. 语义相近但不相同的 subgroup label

这三类负样本的目的分别是：

- 防止模型只学会“看到 familiar token 就判支持”
- 测试时间窗粒度区分能力
- 测试 subgroup 标签近义混淆能力

### 3.7 `uncertain` 的触发条件

`uncertain` 必须作为正式标签，而不是自由裁量。只有以下情况允许输出 `uncertain`：

1. 文本证据不足
2. 只能支持更粗粒度的 time bucket，无法支持 gold 精细值
3. 存在多个 plausible interpretation，当前输入无法消解

不允许把 `uncertain` 当作“模型没把握就默认输出”的逃生口；结果分析中需单独汇报其比例。

### 3.8 指标

`subgroup` 和 `timepoint` 分开汇报以下指标：

- support accuracy
- support macro-F1
- supported-class recall
- conditional grounding normalized exact match

附加结构指标：

- `joint_support_consistency`
  - 两者都判 `supported`、都判 `not_supported`、或一方明显不一致的比例
- `uncertain_rate`

### 3.9 baseline

至少实现以下 baseline：

1. lexical overlap heuristic
2. regex timepoint heuristic
3. subgroup retrieval heuristic
4. prompt-only LLM support classifier

baseline 设计目标是给出可解释下界，而不是追求最优性能。

### 3.10 常见错误类型

需单独分桶：

- `supported` vs `not_supported` confusion
- `uncertain` overuse
- subgroup label grounding failure
- timepoint granularity mismatch
- official item understood but unsupported in study text

### 3.11 本实验最终产出

- `subgroup support` 结果表
- `timepoint support` 结果表
- `conditional grounding` 结果表
- `joint support consistency` 表
- 若干失败案例

---

## 4. 主实验二：Open-world Proposal

### 4.1 任务目标

不给官方 `subgroup` / `timepoint` 值，只给 official parent context，让模型主动提出当前 study 下它认为成立的全部 `subgroup`、`timepoints` 和 linked pairs，再检查其对 official gold 的覆盖情况，以及多提出来的内容是否合理。该实验测的是开放场景下的主动提出与 gold 覆盖能力。

### 4.2 评测单元

输入单元固定为：

```text
(review, study, outcome_concept, comparison)
```

不提供：

- `subgroup`
- `timepoints`

### 4.3 输入

- `SR title`
- `SR PICO`
- 当前 study 的证据文本：
  - 主设置：`full-text`
  - 对照设置：`abstract-only`
- official parent context：
  - `outcome_concept`
  - `comparison`

### 4.4 输出

统一结构如下：

```json
{
  "subgroups": ["..."],
  "timepoints": ["..."],
  "pairs": [
    {
      "subgroup": "...",
      "timepoint": "..."
    }
  ]
}
```

其中：

- `subgroups` 表示模型主动提出的 subgroup 集合
- `timepoints` 表示模型主动提出的 timepoint 集合
- `pairs` 表示模型认为成立的 `(subgroup, timepoint)` 配对

### 4.5 gold 构造

在给定 `(review, study, outcome_concept, comparison)` 下，聚合所有 official analysis-items，形成：

- gold subgroup set
- gold timepoint set
- gold pair set

构造规则：

- subgroup 取该 parent context 下所有 official subgroup 去重后的集合
- timepoint 取该 parent context 下所有 official timepoint 去重后的集合
- pair 由 official item 原始 `(subgroup, timepoint)` 结构直接构成

不要求 prediction 与 gold 一样“只提 gold”；额外预测进入单独审计。

### 4.6 指标

该实验也是正式主实验，但其指标必须与实验一分开解释。主指标固定为三组：

#### 4.6.1 Gold Coverage

- subgroup recall on gold
- timepoint recall on gold
- pair recall on gold

#### 4.6.2 Matched Exactness

仅对成功命中的 gold 值计算：

- subgroup normalized exact match
- timepoint normalized exact match
- pair normalized exact match

#### 4.6.3 Extra Audit

- `supported_extra_count`
- `unsupported_extra_count`
- `conflicting_extra_count`

precision 可作为参考列报告，但不能把“没提到”解释为 `not_supported`，也不能把 extra prediction 直接汇总进主错误。

### 4.7 extra 审计定义

extra prediction 必须进入单独审计，定义写死如下：

- `supported_extra`：文本支持，但 official gold 未包含
- `unsupported_extra`：文本没有足够支持，但也不明显冲突
- `conflicting_extra`：与 official item 或文本证据明显冲突

结果解释时必须明确：

- `supported_extra` 不进入主错误
- `unsupported_extra` 作为风险信号单独报告
- `conflicting_extra` 视为真正错误

### 4.8 baseline

至少实现：

1. regex / lexicon proposal baseline
2. heuristic study-text mining baseline
3. prompt-only LLM proposal baseline

baseline 不追求“和 gold 完全一致”，而是用于衡量覆盖能力与 extra 行为。

### 4.9 常见错误类型

需单独分桶：

- gold subgroup miss
- gold timepoint miss
- pair coverage miss
- reasonable extra beyond gold
- unsupported hallucinated extra
- extracted values correct but linked wrong

### 4.10 本实验最终产出

- subgroup gold recall 表
- timepoint gold recall 表
- pair gold recall 表
- matched exactness 表
- extra audit 表
- 若干典型案例

---

## 5. `pair` 的处理方式

为避免方案膨胀，`pair` 不单独升格成第三个正式主实验，但在两个主实验中都必须被正式汇报。

### 5.1 在实验一中

汇报：

- `joint_support_consistency`
- conditional pair grounding exactness

### 5.2 在实验二中

汇报：

- pair recall on gold
- pair matched exactness
- pair-level extra audit

如果后续分析表明“模型会抽值但不会配对”是主要瓶颈，再新增可选实验：

- `Pair Linking`

但它不属于首轮正式主方案。

---

## 6. Normalization 规则

### 6.1 `timepoint` normalization

允许：

- lowercasing
- whitespace collapse
- punctuation normalization
- `postintervention` / `post-intervention`
- `at 1 month` / `1 month`

不允许：

- 自动把具体时间点压成短期 / 长期桶
- 自动合并不同 follow-up windows

### 6.2 `subgroup` normalization

只允许轻量文本归一化：

- lowercasing
- whitespace collapse
- 标点统一

不做激进 canonicalization：

- 不自动把 grouped intervention 标签映射成具体药物名
- 不自动把 author-defined subgroup 合并成上位类

### 6.3 `pair` normalization

pair 的标准化遵循以下原则：

- `subgroup` 与 `timepoint` 分别先按各自规则标准化
- 标准化后再做 pair-level 匹配
- 不允许在 pair 级别跨字段做语义替换

---

## 7. 结果汇报规范

文档最后的结果规范必须体现：实验一和实验二**同级并列展示**，没有主次附属措辞。

### 7.1 结果章节结构

1. 实验一结果：`Official Item Support`
2. 实验二结果：`Open-world Proposal`
3. 两个实验的对照分析

### 7.2 必报结果

实验一必须报告：

- subgroup support 表
- timepoint support 表
- conditional grounding 表
- joint support consistency 表

实验二必须报告：

- subgroup gold recall 表
- timepoint gold recall 表
- pair gold recall 表
- matched exactness 表
- extra audit 表

### 7.3 对照分析

至少包含以下三类：

- support 强但 proposal 弱的样本
- proposal recall 高但 extra 多的样本
- subgroup 与 timepoint 表现不一致的样本

### 7.4 输入设置

两个实验都统一跑：

- `full-text` 作为主设置
- `abstract-only` 作为对照设置

`relevant-passages` 可以写入扩展实验，但不作为首轮必跑。

---

## 8. 首轮 baseline 与执行顺序

首轮 baseline 不要过重，优先保证两大主实验都能跑通。

### 8.1 实验一 baseline 顺序

1. lexical overlap heuristic
2. regex timepoint heuristic
3. subgroup retrieval heuristic
4. prompt-only LLM support classifier

### 8.2 实验二 baseline 顺序

1. regex / lexicon proposal baseline
2. heuristic study-text mining baseline
3. prompt-only LLM proposal baseline

### 8.3 首轮不做

- pair-only 第三正式实验
- aggressive subgroup canonical taxonomy
- benchmark1 正式打分接入

---

## 9. 当前边界

本方案明确只讨论 benchmark2 中 `timepoint` / `subgroup` 的正式评测，不覆盖：

- benchmark1 主评分接入
- review-level end-to-end candidate generation
- `reported_outcome_measures` 正式评测
- `pair linking` 独立正式实验

这些内容可在后续扩展方案中单独处理。
