# Module 3: EBM Annotation and Analysis — 当前实现说明

- **Status:** reference
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** Current implementation in `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/*` and `application/run_pipeline.py`.

## 1. 目标与范围

本文档描述当前仓库中已经落地的 Module 3 实现行为（而非理想化设计）。

- 输入：Module 2 返回的 `candidates`、`question_expansion` 里的 `pico` / `eligibility_criteria` / `preliminary_analysis_plan`
- 输出：`Module3AnalysisResult`，并由 Phase 5 orchestrator 写入 trace + `run.result`
- 不覆盖：数据库持久化、缓存策略、异步队列、WebSocket 推送

## 2. 真实执行流程

Module 3 的业务阶段是 6 段：

1. `screening`
2. `planning`
3. `extraction` 与 `rob` 并发
4. `aggregation`
5. `grade`

在 Phase 5 orchestrator 的 trace 中，当前会记录 7 个 Module3 step（包含兼容汇总 step）：

1. `module3_screening`
2. `module3_planning`
3. `module3_extraction`
4. `module3_rob`
5. `module3_aggregation`
6. `module3_grade`
7. `module3_analysis`（兼容汇总 payload）

因此 `/trace` 的完整 step 顺序是 11 个：

1. `question_expansion`
2. `question_pi_extraction`
3. `query_generation`
4. `local_search`
5. `module3_screening`
6. `module3_planning`
7. `module3_extraction`
8. `module3_rob`
9. `module3_aggregation`
10. `module3_grade`
11. `module3_analysis`

## 3. 并发与顺序保证

### 3.1 阶段级并发

- `module3_extraction` 与 `module3_rob` 使用 `asyncio.gather(...)` 并发执行。
- `module3_aggregation` 等待 extraction 完成后执行。
- `module3_grade` 等待 aggregation 与 rob 输出后执行。

### 3.2 阶段内并发（按 study / analysis fan-out）

三个环境变量控制并发度，默认均为 `8`：

- `MODULE3_SCREENING_CONCURRENCY`
- `MODULE3_EXTRACTION_CONCURRENCY`
- `MODULE3_ROB_CONCURRENCY`

行为规则：

- 若显式参数 `concurrency` 是正整数，则优先用该值。
- 否则读取对应环境变量。
- 环境变量非法或小于等于 0 时回退默认值 `8`。

### 3.3 输出顺序

并发执行时仍保留输入顺序：

- screening 结果按候选文献原顺序回填。
- extraction 按 `study_index * len(analyses) + analysis_index` 回填。
- rob 按 evidence context 原顺序回填。

## 4. 失败降级（当前真实行为）

### 4.1 Screening 失败

单条 study 失败时：

- 该 study 默认 `included=True`（保守纳入）
- `rationale` 固定为 fallback 文案
- 在 `decision.warning` 和 `screening.warnings` 记录错误

### 4.2 Extraction 失败

单条 `study x analysis` 失败时：

- 生成一条 `ExtractedDataRow`
- `extraction_status="missing"`
- `missing_reason` 写入异常信息
- 并将 warning 记录到 `extraction.warnings`

### 4.3 Risk of Bias 失败

单条 study 失败时：

- 生成 `RiskOfBiasAssessment(overall="unclear")`
- 强制附带 `selective_reporting=unable_to_determine` 域
- warning 同时写入 assessment 与 `risk_of_bias.warnings`

### 4.4 GRADE 失败

单条 analysis 失败时：

- 生成 fallback `GradeAssessment`
- `certainty="very_low"`
- `downgrade_reasons` 固定包含无法完成评估提示
- warning 写入 `grade.warnings` 与条目内 `warnings`

## 5. Aggregation 的已实现边界

`MetaAnalysisAggregator` 当前只做这些事情：

1. 把 `ExtractedDataRow` 转 `StudyData`
2. 用本地 `StatsEngine` 计算 study-level effect
3. 用 `StatsEngine.pool_effects(...)` 做 pooling
4. 用 `StatsEngine.compute_heterogeneity(...)` 计算异质性
5. 对不可计算行标记 `excluded_rows` + warning

不会在文档层承诺尚未实现的复杂自动派生策略或额外智能补全。

## 6. 输入/输出契约（按 dataclass 字段）

以下字段名与 `models.py` 保持一致。

### 6.1 Screening

- `ScreeningDecision`: `study_id`, `title`, `included`, `rationale`, `exclusion_reason`, `warning`
- `ScreeningResult`: `included`, `excluded`, `decisions`, `warnings`

### 6.2 Planning

- `AnalysisSpec`: `analysis_id`, `outcome`, `outcome_type`, `effect_measure`, `intervention`, `comparator`, `timepoint`, `pooling_method`, `model`, `notes`
- `PlanningResult`: `analyses`, `warnings`

### 6.3 Evidence / Extraction

- `EvidenceContext`: `study_id`, `title`, `abstract`, `methods`, `results`, `tables`, `source_path`, `full_text_available`
- `ExtractedDataRow`: `study_id`, `analysis_id`, `outcome_type`, `effect_measure`, `extraction_status`, `missing_reason`, `exp_mean`, `exp_sd`, `exp_n`, `ctrl_mean`, `ctrl_sd`, `ctrl_n`, `exp_events`, `ctrl_events`, `giv_effect`, `giv_se`, `evidence_spans`, `notes`
- `ExtractionResult`: `rows`, `warnings`

### 6.4 Risk of Bias

- `RoBDomainJudgement`: `domain`, `judgement`, `rationale`, `evidence`
- `RiskOfBiasAssessment`: `study_id`, `domains`, `overall`, `warnings`
- `RiskOfBiasResult`: `assessments`, `warnings`

### 6.5 Aggregation

- `StudyAggregation`: `study_id`, `analysis_id`, `included`, `effect`, `se`, `variance`, `weight`, `ci_low`, `ci_high`, `excluded_reason`
- `AnalysisAggregation`: `analysis_id`, `outcome`, `effect_measure`, `study_effects`, `pooled_result`, `heterogeneity`, `excluded_rows`, `warnings`
- `AggregationResult`: `analyses`, `warnings`

### 6.6 Grade

- `GradeAssessment`: `analysis_id`, `certainty`, `downgrade_reasons`, `rationale`, `warnings`
- `GradeResult`: `assessments`, `warnings`

### 6.7 Module3 汇总对象

- `Module3AnalysisResult`:
  - `screening`
  - `planning`
  - `evidence`
  - `extraction`
  - `risk_of_bias`
  - `aggregation`
  - `grade`
  - `warnings`

## 7. 对外可观察行为（Phase 5 / Phase 6）

- `/pipeline/runs/{run_id}/trace` 中以 `steps[*].name` 观察 11-step 执行轨迹（含 7 个 Module3 step）。
- `run.result` 直接暴露：
  - `result.screening`
  - `result.planning`
  - `result.extraction`
  - `result.risk_of_bias`
  - `result.aggregation`
  - `result.grade`
- `module3_analysis` 是兼容汇总 step，payload 包含上述 Module3 子结果，便于旧前端读取。

## 8. 与前端 timeline 的关系

当前 `frontend/gradio_app.py` 的 timeline 是聚合显示：

- `question_expansion`
- `question_pi_extraction`
- `query_generation`
- `local_search`
- `module3_analysis`

它不逐条显示 7 个 Module3 backend step。要看分阶段细节，请使用 `/trace` JSON。
