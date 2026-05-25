# Review-Level Analysis Setting Benchmark 评测方案（v1）

## 子任务 0：定义统一评测前提

本方案面向当前 `review-level analysis setting benchmark`。当前 benchmark 的 sample unit 是 `review`，每个 sample 的输入由以下三部分组成：

- `SR title`
- `SR PICO`
- `included studies` 的证据文本：
  - `abstract`
  - `full text`
  - 或后续构造出的 `relevant passages`

gold 仍然来自 `gold_partial_analysis_settings`，但本方案不再把整条 candidate 当作唯一评测对象，而是拆成多个子任务分阶段评测。

本轮主测字段与角色如下：


| 字段                          | 当前是否主测 | 在本轮方案中的角色               |
| --------------------------- | ------ | ----------------------- |
| `outcome_concept`           | 否      | gold-given 锚点           |
| `data_type`                 | 是      | 统计设定分类目标                |
| `candidate_effect_measure`  | 是      | 条件化统计设定分类目标             |
| `comparisons`               | 是      | review-level 比较结构恢复目标   |
| `arm_pairs`                 | 是      | comparison grounding 目标 |
| `reported_outcome_measures` | 否      | 表层测量实现层，暂不主测            |
| `subgroup_candidates`       | 否      | 延后字段                    |
| `timepoints`                | 否      | 延后字段                    |


本轮方案统一采用以下前提：

- `outcome_concept` 作为 gold-given 锚点。
- 所有正式评测子任务都默认“给定一个 gold `outcome_concept`”。
- 这样做的目的有两个：
  - 避免 outcome 生成错误污染下游字段评测；
  - 把任务拆成更清晰的能力单元，便于分析模型到底错在统计设定、比较结构，还是 grounding。

这意味着本轮方案不是端到端 candidate generation 评测，而是以 `outcome_concept` 为条件的字段级、结构级评测。

---

## 子任务 1：构造统一输入证据

所有阶段共用同一套输入构造逻辑。给定一个 `(review, outcome_concept)`，模型看到的输入不是抽象的“evidence”，而是实际文献文本。初版定义三种输入设置：

1. `abstract-only`
2. `full-text`
3. `relevant-passages`

### 1.1 `abstract-only`

- 对每篇 included study，仅提供 `abstract`
- 若 study 没有 abstract，则该 study 在该设置下不提供文本
- 该设置用于模拟最低证据可得性场景，也适合作为初版 baseline

### 1.2 `full-text`

- 对每篇 included study，优先提供 cleaned `full text`
- 若 study 无 full text，则退化为 `abstract`
- 该设置作为当前主实验设置之一

### 1.3 `relevant-passages`

- 从 full text 或 abstract 中检索与目标 `outcome_concept` 相关的段落
- 检索可基于以下信号：
  - outcome 关键词
  - intervention / comparison 关键词
  - 候选 effect-measure 关键词
- 多篇 studies 的相关段落按 study 为单位拼接
- 该设置作为增强设置保留，初版不要求先实现到位

### 1.4 输入拼接格式

建议统一保留以下 study 级上下文：

- `study_id`
- `study_year`
- `primary_report.title`
- `evidence_tier`

推荐拼接顺序：

1. 先按 study 排序，建议使用 benchmark 内现有顺序或 `study_id`
2. 每篇 study 先给 study header，再给正文证据
3. 多篇 study 顺序保持稳定，避免同一 sample 多次运行输入位置波动

推荐长度控制：

- `abstract-only`：通常不额外截断
- `full-text`：按 study 截断，优先保留标题、摘要、方法、结果相关段落
- `relevant-passages`：每篇 study 保留 top-k 段，k 在实现阶段固定

### 1.5 本轮选择

初版 baseline 至少跑两种输入设置：

- `abstract-only`
- `full-text`

`relevant-passages` 作为增强设置在方案中保留，但可延后实现。

本子任务最终产出：

- 一份统一输入 schema
- 三种输入设置的正式定义
- 一张输入设置对比表

---

## 子任务 2：`data_type` 评测

### 2.1 任务目标

在给定 gold `outcome_concept` 的条件下，评测模型是否能判断正确的 `data_type`。该任务单独存在，因为：

- `data_type` 是后续 `candidate_effect_measure` 评测的前置条件；
- 它是当前 benchmark 中最稳定的统计设定字段之一；
- 它本质上是一个条件化分类任务，适合作为字段级评测入口。

### 2.2 输入

- `SR title`
- `SR PICO`
- 与该 outcome 相关的 included-study evidence text
- gold `outcome_concept`

### 2.3 输出

- 单值 `data_type`

### 2.4 评测单元

```text
(review, outcome_concept) -> data_type
```

### 2.5 gold 构造

需要先从 gold candidates 中聚合同一 `(review, outcome_concept)` 下的 `data_type`。正式实现前需先做一次统计检查：

- 是否存在同一 `review + outcome_concept` 对应多个 `data_type`
- 若不存在或极少，可将该任务按单标签分类处理
- 若存在非忽略级别的多标签情况，需在方案中固定规则：
  - 推荐优先拆成多个实例；
  - 不推荐保留“dominant label”，除非数据统计表明多标签几乎全为噪声

当前默认建议：优先采用“拆成多个实例”的规则，保证定义完整，不把真实多义性压平。

### 2.6 指标

- Accuracy
- Macro-F1
- confusion matrix
- per-class support

推荐主指标为：

- `Accuracy`：用于直观汇报
- `Macro-F1`：用于控制类不平衡影响

### 2.7 baseline

至少实现三类 baseline：

1. 全局 majority baseline
2. 基于 outcome surface pattern 的简单规则 baseline
3. prompt-only LLM baseline

规则 baseline 可以使用的弱信号包括：

- `incidence`, `risk`, `mortality`, `cessation` 等倾向于 `Dichotomous`
- `score`, `scale`, `mean change`, `symptom severity` 等倾向于 `Continuous`
- `survival`, `hazard` 等倾向于 `Contrast level`

### 2.8 常见错误分析

需单独归档以下错误：

- `Dichotomous` vs `Continuous` 混淆
- `Contrast level` 误判为前两类
- 证据不足导致的误判
- outcome wording 误导导致的误判

### 2.9 本子任务最终产出

- 主结果表
- confusion matrix
- 若干失败案例

---

## 子任务 3：`candidate_effect_measure` 评测

### 3.1 任务目标

在给定 gold `outcome_concept` 和 `data_type` 的条件下，评测模型是否能判断正确的 `candidate_effect_measure`。该任务单独测的原因是：

- 它强依赖 `data_type`
- 但又不是 `data_type` 的机械映射
- 模型仍需结合 evidence 和 meta-analysis 语境做判断

### 3.2 输入

- `SR title`
- `SR PICO`
- 与该 outcome 相关的 evidence text
- gold `outcome_concept`
- gold `data_type`

可选补充实验：

- 使用 predicted `data_type` 替换 gold `data_type`，观察级联误差

### 3.3 输出

- 单值 `candidate_effect_measure`

### 3.4 评测单元

```text
(review, outcome_concept, data_type) -> candidate_effect_measure
```

### 3.5 gold 构造

需要聚合同一 `(review, outcome_concept, data_type)` 下的 effect measure，并统计是否存在一对多情况。

正式规则建议：

- 若同一 `(review, outcome_concept, data_type)` 出现多个 effect measure，优先拆成多个实例；
- 不建议用频率最高值强行覆盖，因为 effect measure 是核心统计设定字段，不应被平滑掉。

### 3.6 指标

- Accuracy
- Macro-F1
- per-`data_type` conditional accuracy
- confusion matrix within each `data_type`

推荐主指标：

- overall Accuracy
- per-`data_type` conditional accuracy

### 3.7 baseline

至少实现：

1. per-`data_type` majority baseline
2. compatibility rule baseline
3. prompt-only LLM baseline

compatibility rule baseline 可基于以下约束：

- `Dichotomous` 常见：`Risk Ratio`, `Odds Ratio`, `Risk Difference`, `Peto Odds Ratio`
- `Continuous` 常见：`Mean Difference`, `Std. Mean Difference`
- `Contrast level` 常见：`Hazard Ratio`

### 3.8 常见错误分析

需单独记录：

- `Risk Ratio` / `Odds Ratio` / `Risk Difference` 混淆
- `Mean Difference` / `Std. Mean Difference` 混淆
- 上游 `data_type` 错误导致的连带误差
- evidence 中不直接出现 effect measure 的情况

### 3.9 本子任务最终产出

- 条件准确率表
- 分 `data_type` 的错误分布表
- gold-typed 与 predicted-typed 两套结果对比

---

## 子任务 4：`comparisons` 评测

### 4.1 任务目标

在给定 gold `outcome_concept` 的条件下，评测模型是否能恢复该 outcome 对应的 review-level `comparisons`。这一阶段单独测的原因是：

- `comparisons` 是 review/synthesis 层的问题
- 它不是 effect-measure 一类的分类任务，而是集合恢复任务
- 它体现的是“review authors 在该 outcome 下实际组织了哪些 pairwise comparison questions”

### 4.2 输入

- `SR title`
- `SR PICO`
- 与该 outcome 相关的 included-study evidence text
- gold `outcome_concept`

### 4.3 输出

- comparison list / set

### 4.4 评测单元

```text
(review, outcome_concept) -> set(comparisons)
```

### 4.5 gold 构造

需从 gold candidates 中聚合该 outcome 下所有 comparisons，并完成：

- 去重
- normalization
- 空 comparison 处理

正式规则建议：

- 空 comparison 默认不进入 gold comparison set
- broad comparison 与 specific comparison 若在 gold 中并列出现，则并列保留
- 不做自动上位归并，避免人工压平 gold 粒度

### 4.6 指标

- exact set match
- precision / recall / F1
- normalized set F1
- comparison count accuracy

推荐主指标：

- normalized set F1
- comparison count accuracy

### 4.7 baseline

至少实现：

1. 从 `SR PICO.I/C` 启发式生成 comparison 候选
2. 从 evidence 文本中抽取 `A versus B` 字符串
3. LLM comparison extraction baseline

PICO heuristic baseline 的作用主要是给出下界，不应被视为正式强 baseline，因为官方 comparison 不等于 I/C 笛卡尔积。

### 4.8 常见错误分析

需单独归档：

- missing comparison
- extra comparison
- grouped comparison vs atomic comparison
- broad vs narrow mismatch
- subgroup mistaken as comparison
- evidence 支持 intervention names，但不支持 review-level comparison grouping

### 4.9 本子任务最终产出

- comparison 集合指标表
- count accuracy 表
- broad/narrow mismatch 案例集

---

## 子任务 5：`arm_pairs` 评测

### 5.1 任务目标

在给定 gold `outcome_concept` 和 gold `comparison` 的条件下，评测模型能否恢复正确的 `arm_pairs`。这一阶段的重点是 grounding，而不是 comparison parsing。

### 5.2 输入

- `SR title`
- `SR PICO`
- 与该 outcome 相关的 evidence text
- gold `outcome_concept`
- gold `comparison`

### 5.3 输出

- `arm_pairs`

### 5.4 评测单元

```text
(review, outcome_concept, comparison) -> set(arm_pairs)
```

### 5.5 gold 构造

需聚合同一 `(review, outcome_concept, comparison)` 下的 arm_pairs，并完成：

需要回答：为什么是只有一个`arm_pairs`，而不是多个`arm_pairs`？

- 去重
- arm 文本 normalization
- direction 统一表示

建议表示为：

```json
{
  "experimental_arm": "...",
  "control_arm": "..."
}
```

### 5.6 指标

- unordered pair precision / recall / F1
- direction accuracy
- exact pair-set match

推荐主指标：

- unordered pair F1
- direction accuracy

这样可以区分：

- 模型是否找对了两边 intervention
- 模型是否把方向判对了

### 5.7 baseline

至少实现：

1. direct parse from comparison baseline
2. evidence-grounded heuristic baseline
3. prompt-only LLM baseline

其中 direct parse baseline 的目标不是拿高分，而是量化“仅靠 comparison 文本能解决多少样本”。

### 5.8 特别分层：parseable vs grounding-required

文档中需要专门加一个小节，把 arm_pair 按来源分成两类：

1. `parseable_from_comparison`
  - comparison 字符串本身可以直接解析出 `A vs B`
2. `requires_evidence_grounding`
  - comparison 为 grouped / abstract label，必须结合 evidence 才能恢复具体 arms

该分层后续既可以作为分析标签，也可以作为单独结果表。

### 5.9 常见错误分析

需单独记录：

- comparison 可解析但 direction 反了
- grouped intervention 无法落地到具体 arms
- multi-arm ambiguity
- comparator 写得过泛
- comparison 正确但 arm grounding 失败

### 5.10 本子任务最终产出

- arm grounding 指标表
- direction 错误率表
- parseable vs grounding-required 分层结果表

---

## 子任务 6：联合 `comparisons + arm_pairs` 评测

### 6.1 任务目标

模拟真实使用场景，让模型一次性输出 comparison 和 arm_pairs。该轨道是辅轨，不替代条件化主轨。

### 6.2 输入

- `SR title`
- `SR PICO`
- 与该 outcome 相关的 evidence text
- gold `outcome_concept`

### 6.3 输出

- comparison list
- each comparison 对应的 arm_pairs

推荐输出结构：

```json
[
  {
    "comparison": "...",
    "arm_pairs": [
      {
        "experimental_arm": "...",
        "control_arm": "..."
      }
    ]
  }
]
```

### 6.4 评测单元

```text
(review, outcome_concept) -> structured(comparisons + arm_pairs)
```

### 6.5 gold 构造

按 outcome 聚合 comparisons，并在每个 comparison 下挂接其对应 arm_pairs，构造成统一结构。

### 6.6 指标

- comparison set F1
- arm_pair set F1
- comparison-arm coherence rate
- exact structured match

其中 `comparison-arm coherence rate` 用于检测：

- arm_pair 是否被挂在正确 comparison 下
- 输出结构是否自洽

### 6.7 baseline

至少实现：

1. single-shot LLM baseline
2. pipeline baseline
  - 先 comparison
  - 再 arm grounding

### 6.8 常见错误分析

需单独记录：

- comparison 对，但 arm_pairs 缺失
- comparison 错，导致 arm grounding 连带错
- arm_pair 被挂在错误 comparison 下
- 结构一致性差

### 6.9 本子任务最终产出

- 联合轨结果表
- 与条件化主轨的对比表
- pipeline vs single-shot 对比表

---

## 子任务 7：统一 gold 预处理与 normalization

这一子任务不直接评模型，但必须先写进方案，不然后续每个阶段都会漂。

### 7.1 要定义的规则

- 文本 normalization 规则
- comparison normalization 规则
- arm text normalization 规则
- 去重规则
- 空值处理规则

### 7.2 推荐 normalize pipeline

建议在 exact/soft match 之前统一进行：

1. lowercasing
2. 去首尾空白与多余空白压缩
3. 去大部分标点
4. `vs` / `versus` 统一

### 7.3 不应过度 canonicalize 的部分

为避免把真实错误抹平，以下内容不建议激进归一化：

- broad vs specific intervention grouping
- grouped intervention label 与具体药物名
- direction 信息
- outcome-specific modifiers

### 7.4 本子任务最终产出

- 一份字段级 normalization 规则表

---

## 子任务 8：统一 baseline 实现清单

该子任务把所有 baseline 放成一个统一执行清单，便于实验按阶段推进。

### 8.1 baseline 分层

每个阶段至少给出三层 baseline：

1. `frequency`
2. `heuristic`
3. `LLM`

### 8.2 每类 baseline 要写清楚的内容

每个 baseline 都必须写明：

- 输入
- 输出
- 是否条件化
- 是否需要 retrieval
- 复杂度
- 适用阶段

### 8.3 推荐执行顺序

建议按以下顺序执行：

1. frequency baselines
2. heuristic baselines
3. prompt-only LLM baselines
4. pipeline baselines
5. enhanced retrieval / relevant-passage baselines

### 8.4 本子任务最终产出

- 一张 baseline 总表
- 一份推荐执行顺序

---

## 子任务 9：统一结果报告模板

这是实验产出的统一规范，目的是避免最后只报一个总 F1。

### 9.1 每个阶段必须报告的内容

每个子任务至少报告：

- 主结果表
- 子类结果表
- confusion matrix 或 error buckets
- 若干失败案例

### 9.2 联合轨报告要求

联合轨和主轨必须并列展示，不能只保留其中一条。

### 9.3 禁止的结果汇报方式

不允许只报一个总 micro-F1 作为全文结论，因为这会重新把不同性质的任务混在一起。

### 9.4 推荐图表

- `data_type` confusion matrix
- `candidate_effect_measure` per-type result table
- comparison count accuracy 分布图
- arm_pair direction error 图
- parseable vs grounding-required 分层表
- 主轨 vs 联合轨对比表

### 9.5 本子任务最终产出

- 一份结果展示模板
- 一份推荐图表列表

---

## 子任务 10：当前边界与后续扩展

最后需要用一个子任务收口，明确本版本不做什么、后续还能怎么扩展。

### 10.1 当前明确不做的评测

- `outcome_concept`
- `reported_outcome_measures`
- `subgroup_candidates`
- `timepoints`

### 10.2 当前方案的限制

- outcome 是 gold-given
- comparison 与 arm_pair 仍受 evidence coverage 影响
- 条件化主轨更像能力上界，不完全等于真实端到端场景

### 10.3 后续扩展方向

- outcome generation evaluation
- reported outcome measure extraction
- subgroup/timepoint evaluation
- candidate-level end-to-end evaluation

### 10.4 本子任务最终产出

- 一份“当前版本边界说明”

---

## 附：推荐的统一结果总表

为保证全文收口清楚，最终建议在文末附一张总表：


| 子任务                        | 输入单元                            | 输出单元              | 主指标                                | baseline 层级                 | 主要错误类型                              |
| -------------------------- | ------------------------------- | ----------------- | ---------------------------------- | --------------------------- | ----------------------------------- |
| `data_type`                | `(review, outcome)`             | `data_type`       | Accuracy / Macro-F1                | frequency / heuristic / LLM | 类型混淆                                |
| `candidate_effect_measure` | `(review, outcome, type)`       | effect measure    | Accuracy / conditional accuracy    | frequency / heuristic / LLM | RR/OR/MD/SMD 混淆                     |
| `comparisons`              | `(review, outcome)`             | set(comparisons)  | set F1 / count accuracy            | heuristic / LLM             | missing/extra/broad-narrow          |
| `arm_pairs`                | `(review, outcome, comparison)` | set(arm_pairs)    | pair F1 / direction accuracy       | parse / heuristic / LLM     | grounding failure / direction error |
| 联合轨                        | `(review, outcome)`             | structured output | exact structured match / coherence | single-shot / pipeline      | structure inconsistency             |


