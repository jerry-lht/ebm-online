# Family-Conditioned Effect Measure 实验进度同步（2026-05-20）

## 1. 当前目标

本轮工作围绕 `candidate_effect_measure` 条件任务展开，前提是：

- 已知 gold `condition_data_type` / family
- 重点优化 family 内部的细粒度判别
- 不再把重点放在 family 分类本身

当前默认运行前提：

- 模型：`gpt-5.4-mini`
- evidence mode：`full-text`
- 并发：`16`

## 2. 已完成的实现

已经完成 `2 x 2` 主消融所需的代码改造，且保持旧实验兼容。

### 2.1 新增可切换策略

`candidate_effect_measure` 现在支持两类正交开关：

- `evidence_strategy`
  - `standard_fulltext_evidence`
  - `family_aware_evidence`
- `decision_strategy`
  - `free_generation`
  - `constrained_selection`

四个主配置已可稳定区分并落到独立结果目录：

- `ft_freegen_baseline`
- `ft_familyevidence_freegen`
- `ft_constrainedselection`
- `ft_familyevidence_constrainedselection`

### 2.2 输入证据侧

已实现 `family_aware_evidence`：

- 仅作用于 `candidate_effect_measure`
- 保留现有 `study_evidence` 主 schema
- 根据 `task_metadata.condition_data_type` 做 family-aware 证据优先
- 无 full text 时自动回退 abstract
- 非 `candidate_effect_measure` 任务保持原行为

### 2.3 决策侧

已实现 `constrained_selection`：

- 输出 schema 不变，仍为 `{"candidate_effect_measure": "..."}`
- family 内候选集固定
- prompt 中加入 family-specific 判别标准

### 2.4 few-shot 钩子

few-shot 接口已接好，首版边界样例文件已加入：

- `code/analysis_setting_experiment/prompts/conditional_candidate_effect_measure_boundary_few_shots_v1/few_shots.txt`

当前 few-shot 还未形成稳定主收益，不建议直接作为正式主配置。

### 2.5 评测与报表增强

`aggregate.json` 已新增：

- `evidence_strategy`
- `decision_strategy`
- `family_internal_confusions`
- `out_of_family_prediction_count`
- `targeted_boundary_errors`

并已保持旧实验结果兼容。

### 2.6 子集与 CLI

已新增固定子集支持，可复现实验：

- `make-conditional-subset`
- `run-conditional`
- `evaluate-conditional`

当前 CLI 默认并发已切到 `16`。

## 3. 已完成验证

### 3.1 本地测试

改动相关测试已通过：

- `16 passed`

### 3.2 真实 API smoke

已完成最小真实链路 smoke：

- `1` 条实例
- `candidate_effect_measure`
- `full-text`
- `family_aware_evidence`
- `constrained_selection`

结论：

- 真实 API 链路通
- 新目录命名正常
- parser / evaluator / aggregate 字段正常

## 4. 已完成实验

### 4.1 dev20：2x2 小规模主消融

固定子集：

- `results/conditional_effect_measure_smoke_v1/conditional_splits/full-text/dev_candidate_effect_measure_dev20.jsonl`

结果：

| 配置 | 含义 | accuracy | macro_f1 |
| --- | --- | ---: | ---: |
| `A0B0` | `standard_fulltext_evidence + free_generation` | `0.45` | `0.2582` |
| `A1B0` | `family_aware_evidence + free_generation` | `0.50` | `0.2863` |
| `A0B1` | `standard_fulltext_evidence + constrained_selection` | `0.50` | `0.2915` |
| `A1B1` | `family_aware_evidence + constrained_selection` | `0.55` | `0.3113` |

阶段结论：

- `A1B1` 在 `dev20` 上最好
- `family_aware_evidence` 有帮助
- `constrained_selection` 也有帮助
- 两者叠加在小样本上最优

边界变化：

- `std mean difference -> mean difference` 有明显改善
- `odds ratio -> risk ratio` 仍顽固
- `peto odds ratio -> risk ratio` 仍顽固
- `risk difference -> risk ratio` 仍顽固
- `mean difference -> mean difference change from baseline` 基本未解决

### 4.2 dev60：基线 vs 小修正版 A1B1

固定子集：

- `results/conditional_effect_measure_smoke_v1/conditional_splits/full-text/dev_candidate_effect_measure_dev60.jsonl`

结果：

| 配置 | accuracy | macro_f1 |
| --- | ---: | ---: |
| `A0B0` | `0.70` | `0.3496` |
| 小修正版 `A1B1` | `0.70` | `0.3141` |

阶段结论：

- 小修正版 `A1B1` 没有在更大子集上站住
- `macro_f1` 低于 `A0B0`
- `OR -> RR` 有局部改善
- 但 `SMD -> MD` 反而变差
- `MD -> change from baseline` 仍未打下

因此，这版“额外强化规则/few-shot”的 prompt 不适合作为正式候选主配置。

### 4.3 test：A0B0 复现实验 vs 历史 full-text 基线

本轮跑的是：

- `A0B0`
- `test`
- `1098` 条 `candidate_effect_measure`
- 模型 `gpt-5.4-mini`
- 并发 `16`

新跑 `A0B0`：

- `accuracy = 0.7359`
- `macro_f1 = 0.4061`

历史 `full-text` 基线：

- `accuracy = 0.7213`
- `macro_f1 = 0.4216`

结论：

- 新跑 `A0B0` 的 `accuracy` 略高
- 但 `macro_f1` 低于历史 `full-text` 基线
- 不能视为更强的新主基线

关键边界观察：

- `MD -> change from baseline`：`69 -> 46`，有改善
- `SMD -> MD`：`67 -> 81`，变差
- `OR -> RR`：无改善
- `Peto OR -> RR`：无改善
- `RD -> RR`：无改善

## 5. 当前阶段结论

截至 `2026-05-20`，可以确认的结论是：

1. `family_aware_evidence` 和 `constrained_selection` 的实现已经完成，实验基础设施可用。
2. 这两个机制在小样本 `dev20` 上显示出正收益，但当前版本尚未在更大样本上稳定复现。
3. 当前最顽固的误差仍集中在 family 内 hardest boundaries，而不是 out-of-family 错误。
4. 历史 `full-text` 基线依然是目前更稳的对照基准。

## 6. 当前最需要攻克的边界

优先级最高的 residual errors：

- `Mean Difference` vs `Mean Difference Change from Baseline`
- `Std. Mean Difference` vs `Mean Difference`
- `Odds Ratio` vs `Risk Ratio`
- `Peto Odds Ratio` vs `Risk Ratio`
- `Risk Difference` vs `Risk Ratio`

其中最值得单独做一轮实验的是：

- `MD` vs `MD Change from Baseline`

因为这条边界在多轮实验里都没有被稳定解决。

## 7. 下一阶段建议

下一环节不建议直接再做大规模全量扫，而建议做“边界定向实验”。

建议顺序：

1. 固定一个中等规模 `dev` 子集或专门的 boundary 子集。
2. 只针对 hardest boundaries 设计更明确的判别 prompt 或 few-shot。
3. 优先验证：
   - `MD` vs `change from baseline`
   - `OR / Peto OR / RD` vs `RR`
4. 先在固定 `dev` 子集上比较：
   - 当前 `A0B0`
   - 原版 `A1B1`
   - 新的 boundary-targeted 版本
5. 只有当 `macro_f1` 和 targeted boundary error 同时改善时，再考虑扩大到 full `dev` 或 `test`

## 8. 关键产物位置

主要结果目录：

- 本轮新实验：`results/conditional_effect_measure_smoke_v1/`
- 历史 `full-text` test 基线：`results/conditional_eval_live_test_fulltext/`

重要文件：

- `dev20` 子集：
  - `results/conditional_effect_measure_smoke_v1/conditional_splits/full-text/dev_candidate_effect_measure_dev20.jsonl`
- `dev60` 子集：
  - `results/conditional_effect_measure_smoke_v1/conditional_splits/full-text/dev_candidate_effect_measure_dev60.jsonl`
- `A0B0 test` 新评测：
  - `results/conditional_effect_measure_smoke_v1/evaluations/gpt-5.4-mini/test/candidate_effect_measure/full-text/ft_freegen_baseline/aggregate.json`
- 历史 `full-text` test 基线：
  - `results/conditional_eval_live_test_fulltext/evaluations/gpt-5.4-mini/test/candidate_effect_measure/full-text/aggregate.json`

## 9. 建议作为下阶段起点的配置

如果下一阶段只选一个起点配置，建议优先保留：

- `A0B0`

原因不是它机制更先进，而是：

- 在当前更大样本验证里更稳
- 便于作为后续边界定向优化的统一对照
- 与历史 `full-text` 主基线口径一致
