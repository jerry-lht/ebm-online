# GRADE Domain: Imprecision

本 domain 评估 GRADE 四域中的不精确性降级判断。评估单位是一个 SoF row 对应的 evidence body。

## 1. 任务边界

method 需要判断效应估计是否因为置信区间过宽、样本量或事件数不足、跨越重要临床阈值等原因而需要降级。

该 domain 不重新计算 pooled estimate；它只基于上游 Meta Analysis 结果和 imprecision evidence 判断精确性。

`method_llm_web` 的第一版实现采用：

```text
setting-level context + numeric evidence
-> contextualization mode: systematic_review_minimally_contextualized
-> LLM web threshold research
-> deterministic decision engine
-> GRADE imprecision judgement
```

LLM 只负责查找 outcome-specific minimally important difference、clinical decision threshold、continuous outcome direction 或 OIS guidance；最终 `downgraded` 和 `levels` 由代码根据 CI、阈值、事件数和样本量确定。threshold research 层不会接收当前 effect estimate 或 CI，避免查询被当前结果牵引。

当前只实现 `systematic_review_minimally_contextualized` mode，即 systematic review / SoF certainty judgement。它允许使用 MID/MCID、clinical importance threshold、non-inferiority margin 和 OIS/sample-size assumption；不使用 guideline recommendation direction、values/preferences、resource use 或 panel benefit-harm tradeoff statement 来直接决定降级。若 guideline/panel 文档明确给出 MID、clinical decision threshold 或 OIS 假设，可以作为 threshold source，但 recommendation 本身不是 judgement。

deterministic engine 采用 GRADE-style 两个证据通道：

- CI approach：优先判断 CI 是否跨 no-effect 或 clinical decision threshold。
- OIS approach：用事件数、样本量、单研究证据和检索到的 OIS guidance 判断 information size 是否足以排除不精确性。OIS 可以独立支持 1 级降级；2 级降级需要 CI 同时跨 important benefit 与 important harm，并伴随 clearly insufficient information size。

连续结局的 `continuous_mid` 会转换为围绕 no-effect 的对称 MID 决策区间；如果 LLM 返回的阈值不能通过 validation，则不进入主决策，只保留在 trace 中。threshold provenance 用于 validation、cache eligibility 和错误分析，不作为最终 judgement 的限幅规则。

## 2. 当前数据分布

<table>
  <thead>
    <tr>
      <th>Dataset</th>
      <th>All</th>
      <th>Smoke</th>
      <th>Dev</th>
      <th>Test</th>
      <th>Schema</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>grade_v3</code></td>
      <td>707</td>
      <td>1</td>
      <td>276</td>
      <td>210</td>
      <td><a href="datasets/grade_v3/schema.md">schema.md</a></td>
    </tr>
  </tbody>
</table>

## 3. 输入依据

<table>
  <thead>
    <tr>
      <th>字段</th>
      <th>作用</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>effect_estimate</code></td>
      <td>效应估计、置信区间和 effect measure。</td>
    </tr>
    <tr>
      <td><code>study_result_rows</code></td>
      <td>样本量、事件数或连续变量结果等 study-level result context。</td>
    </tr>
    <tr>
      <td><code>domain_evidence</code></td>
      <td>不精确性相关证据，例如 CI 宽度、事件数、样本量或是否跨越重要阈值。</td>
    </tr>
  </tbody>
</table>

method 不应使用以下字段作为 prediction 依据：

- `sof_context.footnote_texts`
- `sof_context` 中除 `population_text` 外的任何 SoF row 文本，包括 comment/effect/participants/studies/table title
- `source_summary_of_findings_span_text` 中的 certainty 或脚注解释
- gold `rationale` / `source_spans`
- `question_text`，因为当前数据中它是 SR 标题，可能直接定位真实 review 或 SoF
- review-level full `question_pico`；当前只允许使用其中的 population/P 字段

推荐使用 `analysis_setting` 中的结构化 outcome、timepoint、comparison arms 和 outcome measure 作为 threshold 查询上下文。对于 benchmark 中的 clinical condition，优先使用 `sof_context.population_text`；若该字段缺失，再回退到 `question_pico.population` / `QuestionPICO.P`，最后才回退到 `analysis_setting.population_scope.label`。

`method_llm_web` 的合法输入白名单：

- `analysis_setting.outcome/comparison/timepoint/population_scope/data_type/effect_measure`
- `question_pico.population` / `QuestionPICO.P`，仅用于 threshold research 的 `condition_context`
- `sof_context.population_text`，仅用于 threshold research 的 `condition_context`
- `effect_estimate.effect_value/ci_lower/ci_upper/data_type/effect_measure/participant_count/study_count`
- `study_result_rows[].result_data` 中的 events/totals 或 continuous numeric fields

其中 threshold research 层只使用 `analysis_setting` 派生出的：

- `condition_context`
- `outcome_concept`
- `outcome_measure_or_scale`
- `timepoint_window`
- `threshold_scale_context`
- `intervention_context` / `comparator_context` 作为辅助适用性背景
- `contextualization_mode`，当前固定为 `systematic_review_minimally_contextualized`

`condition_context` 是合并后的单一字段，不会同时把 SoF population 和 analysis setting population 传给 LLM：

```text
condition_context =
  cleaned sof_context.population_text
  else cleaned question_pico.population / QuestionPICO.P
  else informative analysis_setting.population_scope.label
  else null
```

threshold research key 只由以下字段构成：

```text
condition_context + outcome_concept + timepoint_window + threshold_scale_context
```

`comparison` 和 `effect_measure` 不进入 key。前者通常影响 applicability，而不是 MID/clinical threshold 的核心定义；后者是 meta-analysis 的表达方式，不是临床重要性阈值本身。

当前实现会在 trace 中写入：

```json
{
  "input_policy": "analysis_setting_plus_question_population_or_sof_population_no_question_text_no_effect_estimate",
  "condition_context_source": "sof_context.population_text",
  "contextualization_mode": "systematic_review_minimally_contextualized",
  "contextualization_mode_source": "method_default",
  "question_population_used_for_threshold_research": false,
  "sof_population_text_used_for_threshold_research": true,
  "question_text_used_for_threshold_research": false,
  "question_pico_used_for_threshold_research": false,
  "effect_estimate_used_for_threshold_research": false
}
```

用于审计 threshold research 只读取 Question P 或 SoF population 作为 clinical condition，没有读取 SoF 脚注/comment/effect 文本、SR 标题、完整 question PICO、当前 CI 或 gold rationale。

## 4. 输出与指标

Gold 和 prediction 都是一个 GRADE domain judgement：

- `judgement.downgraded`
- `judgement.severity`
- `judgement.levels`
- `judgement.level_evaluable`

兼容指标：

- `all_fields_exact_rate`
- `downgraded_exact_rate`
- `severity_exact_rate`
- `levels_exact_rate`
- `evaluable_exact_rate`

主要指标：

- `downgrade_precision_on_evaluable`
- `downgrade_recall_on_evaluable`
- `downgrade_f1_on_evaluable`
- `level_macro_precision_on_evaluable`
- `level_macro_recall_on_evaluable`
- `level_macro_f1_on_evaluable`
- `level_ordinal_mae_on_evaluable`

`unclear` 不参与主 PRF/MAE 分母。若 gold 或 prediction 的 `level_evaluable=false`、`levels="unclear"` 或 `downgraded="unclear"`，该样本会从主 level metrics 中排除，并单独进入：

- `gold_unclear_count`
- `prediction_unclear_count`
- `prediction_unclear_rate`
- `evaluable_coverage`

LLM threshold research 的辅助指标：

- `threshold_found_rate`
- `threshold_applicable_rate`
- `threshold_query_key_count`
- `threshold_reuse_count`
- `threshold_source_type_distribution`
- `threshold_evidence_grade_distribution`
- `cache_eligible_threshold_count`
- `llm_reasoned_fallback_count`
- `hardcoded_fallback_count`
- `threshold_confidence_distribution`
- `llm_failure_count`
- `strict_source_backed_eval`
- `weak_threshold_eval`
- `fallback_threshold_eval`

threshold 来源分三层：

- `source_backed`：LLM web 找到可审计 URL 支撑的阈值，未来可作为 cache 候选。
- `llm_reasoned_fallback`：没有 source-backed 阈值时，LLM 为当前 instance 给出的低置信 fallback；不允许进入 cache。
- `hardcoded_fallback`：LLM 失败、输出无效或 fallback 无效时，代码使用最后兜底；不允许进入 cache。

`source_backed` 会进一步按 evidence grade 分层：

- `source_backed_direct`：来源直接给出当前 outcome/scale 适用的 MID/MCID、clinical decision threshold、non-inferiority margin 或 guideline panel threshold。
- `source_backed_derived`：来源给出可复现的 clinically important difference 或 sample-size/OIS 假设，并能透明推导到当前 threshold scale。
- `source_backed_indirect`：来源是 clinical threshold，但 population、scale、timepoint 或 outcome applicability 间接。
- `general_grade_default`：GRADE 通用相对效应阈值等一般方法学默认值；不进入 cache，不等同于 outcome-specific direct threshold。
- `llm_reasoned_fallback`：LLM 在无 source-backed 阈值时生成的低置信临床 fallback；不进入 cache。
- `unavailable`：没有可用阈值，或返回数字无法证明是 clinical decision threshold。

分层评估用于诊断 threshold 质量：

- `strict_source_backed_eval` 只统计 `source_backed_direct` 和 `source_backed_derived`。
- `weak_threshold_eval` 统计 indirect、general default、LLM fallback 和 unavailable 等弱阈值来源。
- `fallback_threshold_eval` 只统计 `llm_reasoned_fallback` 和 `hardcoded_fallback`。

这些分层指标不会替代总体 PRF，而是用于区分错误来自 threshold research 质量还是 deterministic decision 逻辑。

这些分层只用于审计和诊断，不改变 deterministic decision engine 的裁决强度：一旦 threshold 通过 validation 且适用于当前 scale，judgement 层按同一套 CI/OIS 规则执行，不因为 `source_backed_indirect`、`general_grade_default` 或 `llm_reasoned_fallback` 等来源标签而人为禁止 2 级或强制降为 1 级。

## 5. Threshold Research Workflow

`method_llm_web` 使用受控的 threshold research workflow，而不是让 LLM 直接判断是否降级：

```text
threshold_context
-> query_plan
-> retrieved_candidates
-> rejected_candidates
-> accepted_threshold
-> normalization
-> source validator
-> deterministic decision engine
```

LLM web search 只能用于寻找外部 threshold evidence，例如 MID/MCID、clinical decision threshold、non-inferiority margin、guideline panel threshold、或 OIS/sample-size 中预设的 clinically important difference。它不能接收当前 effect estimate、CI、SoF footnote、SoF comment、review title 或 gold rationale，也不能直接输出最终 downgrade judgement。

validated threshold 会在 trace 中保留 `research_workflow`、`accepted_candidates`、`rejected_materials`、`threshold_validation_notes` 和 `threshold_evidence_grade`，用于审计是否把 observed effect、diagnostic cutoff、severity cutoff 或 disease definition 错当成 imprecision threshold。

## 6. Threshold Evidence Registry

method 层提供 process-local `ThresholdEvidenceRegistry` 接口。默认实现只缓存通过 validator 的 source-backed threshold：

```text
source_backed_direct
source_backed_derived
```

以下内容不会进入 registry：

- `llm_reasoned_fallback`
- `hardcoded_fallback`
- `source_backed_indirect`
- `general_grade_default`
- validator 标记为 invalid 或 rejected 的 threshold

benchmark 指标会记录：

- `threshold_registry_hit_count`
- `threshold_registry_stored_count`

## 7. 运行

```bash
PYTHONPATH=backend/src python benchmark/online_pipeline/grade/imprecision/evaluation/runner.py \
  --method method_test \
  --run-id smoke-imprecision
```

运行 LLM web 方法的 5 篇 smoke：

```bash
PYTHONPATH=backend/src:. python benchmark/online_pipeline/grade/imprecision/evaluation/runner.py \
  --method grade.method_llm_web \
  --dataset benchmark/online_pipeline/grade/imprecision/datasets/grade_v3/splits/dev \
  --review-limit 5 \
  --max-rows-per-review 3 \
  --workers 4 \
  --run-id imprecision-llm-web-smoke-5
```

`--workers` 会并行执行 threshold research。runner 会按 threshold research key 去重：同一个 condition/outcome/timepoint/threshold scale 只检索一次，其他 row 复用 threshold 并用各自 CI、事件数和样本量重新执行 deterministic decision。

需要本地 LLM 配置：

```text
llm.local.json or LLM_CONFIG_PATH
api_mode must be responses
```

结果写入：

```text
benchmark/online_pipeline/grade/imprecision/runs/<run_id>/
```

`method_llm_web` 还会写出：

```text
threshold_traces.jsonl
```

该文件是审计日志，不是 cache。
