# Analysis-Setting 评估问题规范设计稿

## 1. 文档目的与适用范围

本文档服务于当前 `analysis-setting` 实验，目标不是复盘某次模型结果，而是统一 `review-level analysis setting` 任务的评估问题定义、问题分类、判定边界和后续 evaluator 改造方向。

这里讨论的对象是：

- 预测 candidate 集合
- benchmark 中的 `gold_partial_analysis_settings`
- 当前程序化 `rigid evaluator`
- 当前 `judge evaluator`

这里不讨论数值抽取，也不试图抽象成跨任务通用规范。

## 2. 当前评估链路与现状锚点

### 2.1 当前任务单位

当前 benchmark 的 sample unit 是 `review`。每个 review 的 gold 是一个 `gold_partial_analysis_settings` 列表，每个 candidate 使用以下字段：

- `outcome_concept`
- `data_type`
- `candidate_effect_measure`
- `comparisons`
- `arm_pairs`
- `subgroup_candidates`
- `timepoints`
- `reported_outcome_measures`

### 2.2 当前 parsing 与结构校验

当前 `parsing.py` 的行为是：

- 只接受 JSON array 根节点
- 每个 candidate 必须包含全部 8 个 schema 字段
- 字段类型必须正确
- 多余字段会被丢弃，不会导致失败
- 空字符串、空列表在 parsing 阶段允许存在

因此，当前第一层结构失败主要来自：

- JSON 不合法
- 根节点不是数组
- 缺字段
- 类型错误
- `arm_pairs` 子结构错误

当前 `invalid_output` 只覆盖这类 parsing/schema 失败，不覆盖“字段为空但类型合法”的情况。

### 2.3 当前 rigid evaluator

当前 `evaluator.py` 的核心流程是：

1. `normalize_text` 统一大小写、去大部分标点、压缩空白。
2. `normalize_candidates` 标准化 candidate。
3. 若 `outcome_concept` 归一化后为空，则该 candidate 被计入 `invalid_candidate_count`，并从内容评估中移除。
4. 对 prediction 做精确去重，重复项计入 `duplicate_prediction_count`。
5. 计算 pair-level 相似度。
6. 用 Hungarian 算法做全局 `1-1` 分配。
7. 只保留相似度 `>= 0.65` 的 pair 作为 rigid match。

当前 rigid similarity 的字段与权重是：

- `outcome_concept`: 0.25，token F1
- `data_type`: 0.15，exact match
- `candidate_effect_measure`: 0.15，exact match
- `comparisons`: 0.20，set F1
- `arm_pairs`: 0.15，set F1
- `subgroup_candidates`: 0.05，set F1
- `timepoints`: 0.05，set F1

注意：

- `reported_outcome_measures` 当前会计算 field score，但 **不进入主匹配权重**。
- `subgroup_candidates` 和 `timepoints` 权重较低，但一旦一边空一边非空，对该字段仍是 0 分。
- Hungarian 会先把问题压成 `1-1`，再做阈值裁剪。

### 2.4 当前 judge evaluator

当前 `judge.py` 的职责不是替代 rigid evaluator，而是对 rigid 结果和部分近邻 pair 做语义判断。

当前 judge pair 构造方式是：

- 所有 rigid match 都进入 judge
- 每个 unmatched pred 只补一个“最像的 gold”
- 每个 unmatched gold 只补一个“最像的 pred”

当前 pair source 有三类：

- `rigid_match`
- `rigid_unmatched_pair`
- `rigid_miss_pair`

当前 judge 输出的语义判定有两档：

- strict semantic match:
  - `equivalent`
  - 或 `partially_equivalent + high confidence`
- loose semantic match:
  - `equivalent`
  - 或任意置信度的 `partially_equivalent`

judge 当前只能处理 pair，不能天然解决 `1-many / many-1 / many-many` 分量问题，也不能对 benchmark 漏标给出最终裁决。

### 2.5 当前汇总输出的根本不足

当前评估把很多不同性质的问题混在了一起：

- 预测真的错
- gold 不完整
- gold 粒度更细
- prediction 粒度更细
- gold 没写但 prediction 可能合理
- rigid miss 但语义接近
- 一对多或多对一被压成 unmatched

结果是：

- 一个 `precision/recall/F1` 很难解释
- `gold=0` 与 `pred=0` 无法按传统 IR 语义理解
- `error_analysis_sample` 只保留 `unmatched_prediction`/`unmatched_gold`，没有统一 taxonomy
- 后续 evaluator 很难增量演化，因为没有共享术语和输出边界

## 3. 当前评估问题的总分类

后续统一采用四层 taxonomy。每层回答不同问题，不能相互替代。

### 3.1 第一层：结构合法性问题

这一层只回答“能不能进入内容评估”，不回答“内容对不对”。

固定使用以下分类：

- `invalid_output`
  - JSON 不合法
  - 根节点不是数组
  - 缺字段
  - 类型错误
  - 非 schema 兼容输出
- `valid_but_empty_prediction`
  - parsing 成功
  - schema 合法
  - candidate 列表为空
- `valid_non_empty_prediction`
  - parsing 成功
  - schema 合法
  - candidate 列表非空

补充约定：

- `candidate outcome_concept 为空` 不属于 `invalid_output`，因为 parsing 仍然成功。
- 这类情况进入横切标签 `invalid_candidates`，并在 evaluator 里通过 `invalid_candidate_count` 留痕。

### 3.2 第二层：观测集合关系问题

这一层回答“在 benchmark 观测层面，pred 和 gold 的集合关系是什么”，不直接回答“prediction 是否 hallucination”。

固定使用以下分类：

- `gold=0, pred=0`
  - 当前 benchmark 视角下的无冲突空集
  - 不能推出真实世界中一定没有 setting
- `gold=0, pred>0`
  - 未被 gold 覆盖的预测
  - 默认命名为 `unexplained_prediction_without_gold_coverage`
  - 不能直接命名为 hallucination
- `gold>0, pred=0`
  - 当前 benchmark 视角下的完全漏召回
  - 允许在误差分析中追加 `coverage/input insufficiency` 等横切标签
- `gold>0, pred>0`
  - 进入内容匹配阶段

对 `gold=0, pred>0` 必须坚持以下原则：

- 当 prediction 提供的是 benchmark 未标的附加信息时，评估不能自动判错。
- 这类情况应先视为“未被 gold 解释的新增信息”，再进一步区分：
  - `supported_extra_detail`
  - `unsupported_extra_detail`
  - `hallucinated_extra_detail`

其中：

- `supported_extra_detail`: 输入证据支持，gold 只是没写
- `unsupported_extra_detail`: 暂无输入证据支持，但也不能证明冲突
- `hallucinated_extra_detail`: 与输入或 review context 冲突，或明显无依据强行生成

### 3.3 第三层：candidate 数量与映射结构问题

这一层回答“pred 和 gold 在候选数量、拆分粒度和映射结构上是什么关系”。

固定使用以下映射形态：

- `1-1`
- `1-many`
- `many-1`
- `many-many`
- `orphan_pred`
- `orphan_gold`
- `duplicate_pred`

定义如下：

- `1-1`: 一个 pred 与一个 gold 对应
- `1-many`: 一个 pred 覆盖多个 gold，常见于 pred 合并表达
- `many-1`: 多个 pred 实际在说同一个 gold，常见于模型过度拆分
- `many-many`: 两边粒度都不一致，单个 pair 无法解释
- `orphan_pred`: 没有 gold 能接住的 pred
- `orphan_gold`: 没有 pred 覆盖到的 gold
- `duplicate_pred`: 多个 pred 实质重复同一 setting

这一层要显式指出当前 evaluator 的盲点：

- Hungarian 只能输出压缩后的一对一视角
- 它不会保留“相关但未分配”的边
- 它会过早把 `1-many / many-1 / many-many` 压成若干 unmatched
- judge 只补最邻近 pair，也不足以恢复 group mapping

后续规范要求：

- 先区分“是否存在内容相关性”
- 再区分“分量的 cardinality 结构”
- 最后才讨论某个 pair 是否 rigid / semantic match

### 3.4 第四层：内容关系问题

这一层回答“相关 pred/gold 之间在内容上是什么关系”，统一用以下术语，不再混用“差一点”“比较像”“基本对上”等表述。

- `rigid_match`
- `semantic_match_strict`
- `semantic_match_loose`
- `unsupported_extra_detail`
- `granularity_mismatch`
- `no_match`

定义如下：

- `rigid_match`
  - 通过当前程序化规则直接匹配
- `semantic_match_strict`
  - rigid 没过，但 judge 认为语义等价，且置信足够高
- `semantic_match_loose`
  - rigid 没过，但 judge 认为部分等价或宽松可接受
- `unsupported_extra_detail`
  - 核心 setting 成立，但 prediction 添加了 gold 未标注的细节，且该细节暂时没有证据支持
- `granularity_mismatch`
  - prediction 和 gold 指向同一大类 setting，但拆分/合并粒度不同
- `no_match`
  - 语义上也不是同一个 setting

补充约定：

- `unsupported_extra_detail` 和 `granularity_mismatch` 不能默认归入 hallucination。
- `supported_extra_detail` 与 `hallucinated_extra_detail` 作为附加的 `evidence_support_status` 标记，不替代上面的 `match_type`。

## 4. 关键问题的细化定义

### 4.1 直接匹配问题

当前 rigid match 的来源已经固定：

- normalize
- field-level similarity
- field weights
- Hungarian `1-1`
- threshold `0.65`

需要明确以下原则：

- `rigid_match` 只代表程序化充分接近，不代表唯一正确匹配
- `rigid_miss` 也不代表一定语义错误
- `rigid evaluator` 的输出只能看作一种压缩视图

当前 rigid match 的主要局限：

- 对 `outcome_concept` 的 canonicalization 敏感
- 对 `comparison` wording 敏感
- 对 `subgroup/timepoint` 空值不对称敏感
- 对 `reported_outcome_measures` 只做辅助打分，不进主权重
- 对 split/merge 结构不友好
- 对 broad candidate 与 narrow candidate 的关系表达能力差

### 4.2 语义匹配问题

judge 的职责应被明确限定为：

- 解释 rigid miss 中哪些是语义接近
- 给 rigid miss 提供内容层面的补充证据
- 不直接替代 rigid evaluator 的结构化输出

judge 的边界也必须写清：

- judge 只能判 pair，不天然解决 group mapping
- judge 对 benchmark 漏标无最终裁决能力
- judge 强依赖 pair 构造策略
- 若 pair 构造不完整，semantic match 会被系统性低估

当前 strict/loose 两档语义匹配的用途应统一为：

- `semantic_match_strict`: 用于主结果校正
- `semantic_match_loose`: 用于误差分析上界

### 4.3 多对多问题

这一类问题当前最容易被误压成大量 unmatched。常见来源包括：

- gold 按 `per-protocol / ITT / subgroup / follow-up window` 分开，pred 合并表达
- pred 把一个 broad setting 过度拆成多个 measure-specific candidate
- 同一 comparison 在 pred 中按 surface wording 拆裂
- pred 和 gold 都是多 comparison、多 arm pair 的聚合体，但聚合边界不同

后续 evaluator 的推荐处理顺序是：

1. 先构造 pred-gold 关系图，而不是先做 Hungarian。
2. 基于弱相关边识别连通分量。
3. 先判定分量属于 `1-1 / 1-many / many-1 / many-many`。
4. 再在分量内部判 `rigid_match / semantic_match / granularity_mismatch / extra_detail / no_match`。

规范上必须明确：

- evaluator 不应先强制压成单 pair，再据此给最终结论
- group relation 和 pair relation 应同时保留

### 4.4 gold 为空或字段为空的问题

“空”必须拆开讨论，不能只谈 review-level 空 gold。

需要区分：

- `review-level gold empty`
- `candidate-level field empty`
- `gold 未标注某个字段`
- `gold 明确为空字段`
- `gold 不关心该字段`
- `gold 省略了该字段粒度`

解释约定如下：

- `gold 明确为空字段`: 当前 gold 值为空列表或空字符串，且这代表标注结果中没有写出该维度
- `gold 未标注某个字段`: 当前 benchmark 无法确认该字段在该例中是否被认真标过
- `gold 不关心该字段`: 任务定义不把该字段当主匹配边界
- `gold 省略了该字段粒度`: gold 只保留较粗 setting，没有展开 timepoint/subgroup/analysis subset

对“pred 提供了 gold 没有的字段”，后续必须先走 `extra_detail` 路线，而不是直接判错，尤其是：

- `timepoints`
- `subgroup_candidates`
- `analysis subset`
- `per-protocol / ITT`

这些字段最容易同时满足两个条件：

- benchmark 可能漏标或省略粒度
- 模型也容易过生成

因此默认处理顺序应是：

1. 先记为 `extra_detail`
2. 再标 `evidence_support_status`
3. 只有明确冲突或明确无依据时才下沉为 `hallucination`

### 4.5 其他横切问题

以下问题不并入四层 taxonomy 本体，但 evaluator 输出必须留痕：

- `benchmark incompleteness`
- `field asymmetry`
- `canonicalization dependency`
- `duplicate predictions`
- `invalid candidates`
- `count bias`
- `coverage/input insufficiency`
- `judge uncertainty`

这些标签对指标解释的影响如下：

- micro recall 容易同时被 under-generation 和 benchmark 拆分压低
- precision 容易被 gold 缺失和附加细节误伤
- `canonicalization rescue` 说明的是后处理价值，不是模型原生能力
- judge 置信度低时，不应把语义判断当硬标签使用

## 5. 立即统一的判定原则

在不改代码前，先统一解释口径。

### 5.1 关于 hallucination 的命名

不再使用：

- `pred>0, gold=0 = hallucination`

改为默认命名：

- `unexplained_prediction_without_gold_coverage`

只有满足以下条件时，才允许把某条预测进一步标成 `hallucination`：

- 预测细节与输入证据冲突
- 或该细节超出任务定义且没有可支持证据
- 或 judge / 人工复核确认属于编造

### 5.2 关于 timepoint / subgroup / subset analysis

对以下维度默认先标为 `extra_detail`，不直接判错：

- `timepoints`
- `subgroup_candidates`
- `per-protocol / ITT`
- `subset analysis`

只有在有冲突证据时，才进一步标成 `hallucinated_extra_detail`。

### 5.3 关于 empty-empty 的解释

对 `gold=0, pred=0`：

- 当前 benchmark 视角下是无冲突空集
- 不能解释为“模型证明本 review 没有 analysis setting”
- 后续汇报时不应把这类 case 与普通 true negative 混同

### 5.4 关于 invalid candidate

若 parsing 成功，但 candidate 在 evaluator 规范化后因 `outcome_concept` 为空被丢弃：

- 结构层仍是 `valid_non_empty_prediction`
- 横切标签加 `invalid_candidates`
- 内容层不应把这类被移除 candidate 混同为普通 unmatched

## 6. 建议的新误差分析输出格式

后续 evaluator 至少新增两类输出：`review-level taxonomy summary` 和 `relation-level artifacts`。

### 6.1 Review-level taxonomy summary

每个 review 至少输出以下字段：

```json
{
  "review_id": "CDXXXXXX",
  "structure_status": "invalid_output | valid_but_empty_prediction | valid_non_empty_prediction",
  "emptiness_case": "gold=0,pred=0 | gold=0,pred>0 | gold>0,pred=0 | gold>0,pred>0",
  "pred_candidate_count_raw": 0,
  "pred_candidate_count_valid": 0,
  "gold_candidate_count_valid": 0,
  "invalid_candidate_count": 0,
  "duplicate_prediction_count": 0,
  "cardinality_summary": {
    "one_to_one_component_count": 0,
    "one_to_many_component_count": 0,
    "many_to_one_component_count": 0,
    "many_to_many_component_count": 0,
    "orphan_pred_count": 0,
    "orphan_gold_count": 0
  },
  "match_summary": {
    "rigid_match_count": 0,
    "semantic_match_strict_count": 0,
    "semantic_match_loose_count": 0,
    "granularity_mismatch_count": 0,
    "extra_detail_count": 0,
    "no_match_count": 0
  },
  "evidence_support_summary": {
    "supported_extra_detail_count": 0,
    "unsupported_extra_detail_count": 0,
    "hallucinated_extra_detail_count": 0,
    "judge_uncertain_count": 0
  },
  "reason_tags": [
    "benchmark incompleteness",
    "field asymmetry"
  ]
}
```

要求：

- `pred_candidate_count_raw` 与 `pred_candidate_count_valid` 分开
- emptiness case 独立输出
- cardinality case 不能只保留 matched/unmatched
- `reason_tags` 保留横切问题

### 6.2 Relation-level artifacts

每条关系至少输出以下字段：

```json
{
  "review_id": "CDXXXXXX",
  "component_id": "comp_0001",
  "pred_indices": [0],
  "gold_indices": [1, 2],
  "relation_type": "1-many",
  "match_type": "granularity_mismatch",
  "pair_source": "graph_component",
  "core_alignment_status": "aligned | partially_aligned | not_aligned",
  "evidence_support_status": "none | supported_extra_detail | unsupported_extra_detail | hallucinated_extra_detail",
  "reason_tags": [
    "timepoint_or_subgroup_mismatch",
    "benchmark incompleteness"
  ],
  "rigid_support": {
    "best_pair_score": 0.71,
    "matched_pairs": [
      {
        "pred_index": 0,
        "gold_index": 1,
        "score": 0.71
      }
    ]
  },
  "judge_support": {
    "strict_semantic_supported": false,
    "loose_semantic_supported": true,
    "judge_confidence": "medium"
  },
  "notes": "pred merges two gold timepoints into one broad setting"
}
```

要求：

- `pred_indices`、`gold_indices` 使用数组，而不是强制单 pair
- `relation_type` 和 `match_type` 分开
- `evidence_support_status` 独立编码
- 保留 rigid/judge 支持证据

## 7. 指标解释的分层方案

后续汇报至少拆成三层，而不是把所有问题塞进一个 F1。

### 7.1 Strict benchmark fidelity

使用：

- 当前 rigid 指标
- 或 rigid + strict semantic 校正后的指标

这一层回答：

- 模型对当前 benchmark 的严格贴合程度

### 7.2 Benchmark-tolerant semantic coverage

把以下问题单独剥离后再看 coverage：

- `reasonable extra detail`
- `granularity mismatch`
- `benchmark incompleteness`

这一层回答：

- 若允许 benchmark 不完备和粒度不一致，模型是否仍覆盖到核心 setting

### 7.3 Open-world error analysis

单独计数以下问题：

- 真 hallucination
- 真漏召回
- benchmark 缺失
- 粒度不一致
- duplicate prediction
- invalid candidate

这一层回答：

- 误差到底来自模型、benchmark、还是 evaluator 结构

## 8. 人工复核闭环

建议加入一个最小人工复核 protocol，专门处理：

- `gold=0, pred>0`
- `extra_detail`
- `granularity_mismatch`

最小流程：

1. 抽样 review
2. 查看输入 abstract / SR context
3. 判断该细节属于：
   - `evidence-supported but gold-missing`
   - `unsupported but plausible`
   - `clearly hallucinated`
4. 将标签写入 taxonomy artifact，不直接回写 gold

用途：

- 修正 taxonomy 的解释层
- 为后续 benchmark 修订提供证据
- 但不在本轮实验中把人工判断硬写成新的 gold

## 9. 按场景定义的测试计划

如果后续按本规范改 evaluator，以下场景必须覆盖。每个场景都应同时说明：

- 当前 evaluator 会怎么判
- 为什么不够好
- 新规范下应如何归类

### 9.1 `gold=0, pred=0`

- 当前 evaluator：
  - `pred_candidate_count=0`
  - `gold_candidate_count=0`
  - `precision=0`
  - `recall=0`
  - `f1=0`
  - 不会触发 `zero_candidate_review_error`
- 不足：
  - 结果数值上像“完全失败”，但观测上并无冲突
- 新规范：
  - `structure_status=valid_but_empty_prediction`
  - `emptiness_case=gold=0,pred=0`
  - 不记为 hallucination 或漏召回

### 9.2 `gold=0, pred>0` 且 pred 是合理 timepoint

- 当前 evaluator：
  - 全部成为 `unmatched_prediction`
  - precision/recall/F1 均被打到 0
- 不足：
  - 无法区分“gold 漏标的合理新增信息”和“模型幻觉”
- 新规范：
  - `emptiness_case=gold=0,pred>0`
  - 默认 `unexplained_prediction_without_gold_coverage`
  - relation 先标 `extra_detail`
  - `evidence_support_status=supported_extra_detail` 或 `unsupported_extra_detail`

### 9.3 `gold=0, pred>0` 且 pred 是明显编造 subgroup

- 当前 evaluator：
  - 同样只是 `unmatched_prediction`
- 不足：
  - 与上一个场景无法区分
- 新规范：
  - `unexplained_prediction_without_gold_coverage`
  - 若与输入冲突，标 `hallucinated_extra_detail`

### 9.4 `gold>0, pred=0`

- 当前 evaluator：
  - `zero_candidate_review_error=True`
  - recall 为 0
- 不足：
  - 无法单独表达输入证据不足或任务本身不可恢复
- 新规范：
  - `emptiness_case=gold>0,pred=0`
  - 默认 `orphan_gold`
  - 可追加 `coverage/input insufficiency`

### 9.5 `1-1 rigid match`

- 当前 evaluator：
  - 正常 `matched_pair_count += 1`
- 不足：
  - 缺少“这是 `1-1` 结构”的显式输出
- 新规范：
  - `relation_type=1-1`
  - `match_type=rigid_match`

### 9.6 `1-1 semantic only match`

- 当前 evaluator：
  - rigid miss
  - 若该 pair 被 judge 构造到，可能出现 semantic strict/loose match
- 不足：
  - 若 pair 未被构造，会直接漏掉
  - 汇总层仍然缺少统一 relation artifact
- 新规范：
  - `relation_type=1-1`
  - `match_type=semantic_match_strict` 或 `semantic_match_loose`

### 9.7 `1-many`：gold 拆成两个 timepoint，pred 合并

- 当前 evaluator：
  - 最多只会保留一个 `1-1` match，其余 gold 变成 unmatched
  - 或整体掉到阈值以下，全部 unmatched
- 不足：
  - 无法表示“核心 setting 一样，只是粒度合并”
- 新规范：
  - `relation_type=1-many`
  - `match_type=granularity_mismatch`

### 9.8 `many-1`：pred 把同一 setting 重复拆成两个 surface form

- 当前 evaluator：
  - 一个 pred 可能匹配，另一个变 orphan
  - 若完全相同则只会计入 `duplicate_prediction_count`
- 不足：
  - 无法区分 surface over-split 和 genuinely different candidate
- 新规范：
  - `relation_type=many-1`
  - 重复者标 `duplicate_pred` 或 `granularity_mismatch`

### 9.9 `many-many`

- 当前 evaluator：
  - 被 Hungarian 压成数个 pair 和更多 unmatched
- 不足：
  - 完全丢失分量结构
- 新规范：
  - `relation_type=many-many`
  - 在 component 内再判内容关系

### 9.10 `pred 提供 extra timepoint，但核心 outcome/comparison 正确`

- 当前 evaluator：
  - 若时间点字段一边空一边非空，会损失该字段分数
  - 可能导致 rigid miss
- 不足：
  - 会把“合理附加细节”和“错误 setting”混为一类
- 新规范：
  - `match_type=unsupported_extra_detail` 或 `semantic_match_* + supported_extra_detail`

### 9.11 `duplicate prediction`

- 当前 evaluator：
  - 只对完全归一化相同的 prediction 计 `duplicate_prediction_count`
- 不足：
  - 不能捕获语义重复但 surface 不同的 over-split
- 新规范：
  - `duplicate_pred` 既支持 exact duplicate，也支持 semantic duplicate

### 9.12 `invalid output`

- 当前 evaluator：
  - parsing 失败，`parse_status=invalid_output`
- 不足：
  - 与内容层错误没有统一断面
- 新规范：
  - 第一层终止内容评估
  - review-level summary 仍然落盘

### 9.13 `candidate outcome_concept 为空`

- 当前 evaluator：
  - parsing 成功
  - evaluator 将其记为 `invalid_candidate_count`
  - candidate 被过滤
- 不足：
  - 当前输出没有把它纳入统一 taxonomy
- 新规范：
  - 结构层仍保留 `valid_non_empty_prediction`
  - 另加 `invalid_candidates`

### 9.14 `reported_outcome_measures` 仅 surface drift，不影响 core setting

- 当前 evaluator：
  - 该字段不进主权重
  - 可能在主匹配上完全不受影响
- 不足：
  - 当前没有把它显式解释为“辅助字段 drift”
- 新规范：
  - 核心匹配继续看 core setting
  - `reported_outcome_measures` drift 作为 `reason_tags` 或附加字段分析输出

## 10. 对当前 evaluator 改造的最小实现建议

本设计稿不冻结最终代码，但建议后续按以下最小路径落地：

1. 保留当前 rigid evaluator，作为 strict benchmark fidelity 的基础层。
2. 在 Hungarian 之前额外保留一份弱相关 pair graph。
3. 在 graph 上识别 component，并输出 `relation_type`。
4. judge 从“每个 unmatched 只找一个 best neighbor”改成“component 内补全候选 pair”。
5. 将 `extra_detail` 与 `hallucination` 明确拆开。
6. 将 `review_results` 与 `error_analysis_sample` 升级为 taxonomy-aware artifacts。

## 11. 本轮实验的统一结论

从本轮开始，以下口径视为默认规则：

- 不再把 `gold 未覆盖 prediction` 默认命名为 hallucination
- `hallucination` 只在冲突或明确无依据时使用
- `timepoint / subgroup / subset analysis` 默认先按 `extra_detail` 处理
- `1-many / many-1 / many-many` 必须作为单独问题类型保留
- `rigid_match` 只是程序化匹配，不是唯一真值
- 后续汇报至少区分 strict benchmark fidelity、benchmark-tolerant semantic coverage、open-world error analysis 三层

这份文档是当前 `analysis-setting` 实验的评估规范设计稿。后续若改 evaluator，所有新增字段、命名和测试场景应优先与本文档对齐。
