# Module 3 简化版测试指南

- **Status:** reference
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** Reference for Module 3 simplified testing workflow.


本文档用于验证 **Phase 4 简化版 Module 3（EBM Annotation and Analysis）**：从 Module 2 候选文献出发，完成 screening、analysis planning、data extraction、Risk of Bias、StatsEngine aggregation 和 GRADE 的最小可跑通闭环。

> 说明：当前 Module 3 不接数据库、不实现缓存、不记录 usage。单元测试包含两类：一类直接 mock gateway 验证业务编排；另一类使用真实 `LLMGateway` 类加 fake OpenAI Responses client，验证 structured-output 通路、prompt/schema 加载和 Module 3 全流程。真实外部 LLM 实例测试见「真实 LLM 实例测试」。

## 当前实现范围

已完成的简化链路：

1. `StudyScreener`：逐篇候选文献调用 LLM，输出 include/exclude、rationale、exclusion_reason。LLM 失败时默认 include 并记录 warning。
   - 并发参数：`MODULE3_SCREENING_CONCURRENCY`，默认 8；并发下结果顺序保持稳定。
2. `AnalysisPlanner`：一次性生成 `AnalysisSpec` 列表。失败时从 PICO / preliminary plan 生成 fallback。
3. `EvidenceContextBuilder`：优先读取 `article_path` 对应 derived article JSON，抽取 abstract、methods、results、tables；无全文时回退到 candidate 的 title/abstract。
4. `DataExtractor`：按 `study x analysis` 调 LLM，抽取原文可见数值和 evidence spans；不做统计推导。
   - 并发参数：`MODULE3_EXTRACTION_CONCURRENCY`，默认 8；单条失败降级为 `extraction_status="missing"`。
5. `RiskOfBiasAssessor`：逐篇评估 RoB 1 可判断域；`selective_reporting` 由系统固定为 `unable_to_determine`。
   - 并发参数：`MODULE3_ROB_CONCURRENCY`，默认 8；单条失败降级为 `overall="unclear"`。
6. `MetaAnalysisAggregator`：不调用 LLM，把 extracted rows 转成 `StudyData`，调用 `StatsEngine` 计算 study effects、pooling 和 heterogeneity。
7. `GradeAssessor`：每条 analysis 调 LLM，基于 aggregation、RoB、缺失数据生成 certainty 和 downgrade reasons。
8. `Module3AnalysisRunner`：串起完整流程。
9. `ebm_backend.online_pipeline.interfaces.cli.evidence_analysis --mock`：使用本地检索结果和 deterministic mock LLM 输出跑通完整 Module 3。
   - 当前 CLI 仅支持 `--mock`，非 mock 路径会直接退出（见 `test_module3_cli_requires_mock`）。

## 相关代码路径

- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/models.py` — Module 3 数据结构
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/screening.py` — Study screening
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/planning.py` — Analysis planning
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/extraction.py` — Evidence context + data extraction
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/rob.py` — Risk of Bias
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/aggregation.py` — StatsEngine aggregation
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/grade.py` — GRADE
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/runner.py` — 端到端 runner
- `backend/src/ebm_backend/online_pipeline/interfaces/cli/evidence_analysis.py` — mock CLI smoke 入口
- `backend/src/ebm_backend/shared/llm/prompts/study_screening.txt`
- `backend/src/ebm_backend/shared/llm/prompts/analysis_planning.txt`
- `backend/src/ebm_backend/shared/llm/prompts/data_extraction.txt`
- `backend/src/ebm_backend/shared/llm/prompts/risk_of_bias.txt`
- `backend/src/ebm_backend/shared/llm/prompts/grade_assessment.txt`
- `backend/src/ebm_backend/shared/llm/schemas/study_screening.json`
- `backend/src/ebm_backend/shared/llm/schemas/analysis_planning.json`
- `backend/src/ebm_backend/shared/llm/schemas/data_extraction.json`
- `backend/src/ebm_backend/shared/llm/schemas/risk_of_bias.json`
- `backend/src/ebm_backend/shared/llm/schemas/grade_assessment.json`
- `tests/unit/test_module3_analysis.py`

## 依赖与前置条件

1. Python 依赖已安装：

   ```bash
   pip install -r requirements.txt
   ```

2. 推荐先确认 Module 1 本地索引存在：

   ```bash
   test -f data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl
   ```

   若不存在，先重建：

   ```bash
   PYTHONPATH=backend/src python -m ebm_backend.index_construction.interfaces.cli index-derived --data-root data/data_for_test/data_demo_with_mesh
   ```

3. Module 3 mock 测试不需要真实 OpenAI API，不需要数据库。

如果没有本地索引，`--mock` CLI 仍会自动注入一个 synthetic candidate，用于完整跑通 Module 3 smoke；有索引时会优先使用真实本地检索候选。

## 自动化测试（推荐先跑）

只跑 Module 3：

```bash
pytest tests/unit/test_module3_analysis.py -q
```

预期：所有测试通过。

覆盖内容：

| 测试 | 说明 |
|------|------|
| `test_screening_include_exclude_split` | Mock LLM 验证 include/exclude 分流，并确认 LLM call 使用 `cacheable=False` |
| `test_planning_generates_analysis_list` | Mock LLM 验证 analysis list 生成 |
| `test_extraction_mock_values_enter_aggregation` | Mock extraction 数值进入 `StatsEngine` aggregation |
| `test_rob_auto_adds_selective_reporting` | RoB 自动补 `selective_reporting=unable_to_determine` |
| `test_module3_runner_complete_flow_and_grade_certainty` | 完整 runner：screening → planning → extraction → RoB → aggregation → GRADE |
| `test_module3_parallel_components_keep_stable_order` | 验证 screening / extraction / rob 在并发场景下输出顺序稳定 |
| `test_module3_parallel_single_item_failures_degrade_not_abort` | 验证单条 screening/extraction/rob 失败时降级继续，不中断全流程 |
| `test_module3_synthetic_rcts_full_flow_through_llm_gateway` | 造 3 篇 synthetic RCT derived JSON，使用真实 `LLMGateway(conn=None)` + fake Responses client 跑完整 Module 3，全程经过 structured output JSON 解析 |
| `test_aggregation_tracks_missing_rows` | 数据不足时 aggregation 不 pooling，并记录 excluded rows |
| `test_evidence_context_builder_reads_article_json` | 从 derived article JSON 抽取 abstract/methods/results/tables |
| `test_module3_mock_cli_outputs_full_result` | CLI mock 输出完整结果 JSON |
| `test_module3_cli_requires_mock` | 当前 CLI 非 mock 路径显式拒绝，避免误打真实 API |
| `test_evidence_context_builder_rejects_legacy_blocks_schema` | legacy `sections[].blocks` schema 会抛错，要求新 `xml_content.sections/text` 结构 |

与 Module 2 和 StatsEngine 一起回归：

```bash
pytest tests/unit/test_module2_question.py tests/unit/test_stats_engine.py tests/unit/test_module3_analysis.py -q
```

## 真实 LLM 实例测试

默认单元测试不访问真实外部 API。需要验证当前配置的真实 LLM 时，显式设置 `RUN_REAL_LLM=1`。

当前已验证的实例配置：

```bash
OPENAI_BASE_URL="https://api.siliconflow.cn/v1"
LLM_MODEL="deepseek-ai/DeepSeek-V4-Flash"
```

如果你的 `.env` 已经配置好，只需要设置 `RUN_REAL_LLM=1`。不再推荐在命令前临时覆盖 `OPENAI_API_KEY`，避免把 shell 旧值和项目 `.env` 混用。

先确认当前运行时读到的配置，不会打印完整 key：

```bash
PYTHONPATH=backend/src python - <<'PY'
from ebm_backend.shared.config.settings import settings

key = settings.openai_api_key or ""
print("has_key:", bool(key))
print("key_prefix:", key[:6] if key else "")
print("base_url:", settings.openai_base_url)
print("model:", settings.llm_model)
PY
```

### 轻量 extraction-only smoke（推荐）

这个测试造 3 篇 synthetic RCT，只调用真实 LLM 做 data extraction，然后用 `StatsEngine` aggregation。它验证真实模型能从 article JSON 中抽取事件数和分母。

合成 RCT 数据如下：

| Study | Duloxetine events / n | Placebo events / n |
|-------|------------------------|--------------------|
| `real-rct-1` | `5 / 100` | `20 / 100` |
| `real-rct-2` | `9 / 120` | `24 / 120` |
| `real-rct-3` | `4 / 80` | `12 / 80` |

```bash
RUN_REAL_LLM=1 PYTHONPATH=backend/src pytest \
  tests/integration/test_module3_real_llm_smoke.py::test_module3_real_llm_extraction_only_synthetic_rcts \
  -q -s
```

预期结果：

```text
1 passed
```

该测试断言：

- 真实 LLM 抽到三篇研究的 `exp_events / exp_n / ctrl_events / ctrl_n`
- extraction rows 都是 `included`
- aggregation 的 `pooled_result.study_count == 3`
- pooled RR 原始尺度 `effect_original < 1.0`

当前验证记录：使用 `deepseek-ai/DeepSeek-V4-Flash` 和 SiliconFlow compatible endpoint，轻量 smoke 通过，用时约 1 分 40 秒。

### 完整 Module 3 real-LLM smoke（较慢）

这个测试造同样的 3 篇 synthetic RCT，但会跑完整 Module 3：

```text
3 screening + 1 planning + 3 extraction + 3 RoB + 1 GRADE = 11 次真实 LLM 调用
```

命令：

```bash
RUN_REAL_LLM=1 PYTHONPATH=backend/src pytest tests/integration/test_module3_real_llm_smoke.py::test_module3_real_llm_extracts_synthetic_rct_counts -q -s
```

当前验证记录：

- 2026-05-10：该完整 smoke 已通过，但 SiliconFlow/DeepSeek 端点耗时约 17 分钟，不建议作为日常回归。
- 2026-05-12：整文件真实 LLM smoke 已再次通过：

  ```bash
  RUN_REAL_LLM=1 PYTHONPATH=backend/src pytest tests/integration/test_module3_real_llm_smoke.py -q -s
  ```

  结果：`2 passed in 1020.72s`。当前耗时主要来自外部 LLM structured-output 调用，不是本地 runner 或 stats 计算。

只跑 synthetic RCT + LLMGateway 全流程测试：

```bash
PYTHONPATH=backend/src pytest tests/unit/test_module3_analysis.py::test_module3_synthetic_rcts_full_flow_through_llm_gateway -q
```

该测试会临时生成 3 篇 RCT article JSON：

| Study | Duloxetine events / n | Placebo events / n |
|-------|------------------------|--------------------|
| `rct-1` | `5 / 100` | `20 / 100` |
| `rct-2` | `9 / 120` | `24 / 120` |
| `rct-3` | `4 / 80` | `12 / 80` |

预期：

- `LLMGateway` 实例真实执行 `call()`。
- fake Responses client 收到 11 次 structured-output 请求：3 screening、1 planning、3 extraction、3 RoB、1 GRADE。
- `EvidenceContextBuilder` 从 3 篇 JSON 读取全文 context。
- extraction rows 包含三篇研究的事件数和样本量。
- aggregation 的 `pooled_result.study_count == 3`。
- pooled RR 原始尺度 `effect_original < 1.0`，表示 mock 数据方向有利于 duloxetine。
- GRADE certainty 为 `moderate`。

## Mock CLI 手动测试

推荐用当前 100 篇索引中真实存在的度洛西汀问题：

```bash
PYTHONPATH=backend/src python -m ebm_backend.online_pipeline.interfaces.cli.evidence_analysis \
  --mock \
  --question "Does duloxetine reduce catheter-related bladder discomfort?" \
  --population "catheter-related bladder discomfort" \
  --intervention "duloxetine" \
  --comparison "placebo" \
  --outcome "catheter-related bladder discomfort incidence" \
  --top-k 3
```

预期输出是一个完整 JSON，顶层字段包括：

```text
screening
planning
evidence
extraction
risk_of_bias
aggregation
grade
warnings
```

重点检查：

- `screening.included` 非空。
- `planning.analyses[0].effect_measure` 为 `RR`。
- `extraction.rows` 中有 `exp_events`、`ctrl_events`、`exp_n`、`ctrl_n`。
- `risk_of_bias.assessments[*].domains` 中包含 `selective_reporting`，且 judgement 为 `unable_to_determine`。
- `aggregation.analyses[0].pooled_result.study_count` 大于 0。
- `grade.assessments[0].certainty` 为 mock 输出的 `low`。

如果你想保存输出方便查看：

```bash
python -m ebm_backend.online_pipeline.interfaces.cli.evidence_analysis \
  --mock \
  --question "Does duloxetine reduce catheter-related bladder discomfort?" \
  --population "catheter-related bladder discomfort" \
  --intervention "duloxetine" \
  --comparison "placebo" \
  --outcome "catheter-related bladder discomfort incidence" \
  --top-k 3 \
  > /tmp/module3_mock_result.json
```

然后查看摘要：

```bash
python - <<'PY'
import json

data = json.load(open("/tmp/module3_mock_result.json", encoding="utf-8"))
print("included:", len(data["screening"]["included"]))
print("analyses:", [a["analysis_id"] for a in data["planning"]["analyses"]])
print("rows:", len(data["extraction"]["rows"]))
print("pooled:", data["aggregation"]["analyses"][0]["pooled_result"])
print("grade:", data["grade"]["assessments"][0]["certainty"])
PY
```

## Python 手动联调

如果你想绕过 CLI，直接调用 runner：

```python
import asyncio

from ebm_backend.online_pipeline.interfaces.cli.evidence_analysis import MockLLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis import Module3AnalysisRunner
from ebm_backend.online_pipeline.application.question_study import EligibilityCriteria, PICO, PreliminaryAnalysisPlan, QueryGenerator, QuestionStudySearcher

question = "Does duloxetine reduce catheter-related bladder discomfort?"
pico = PICO(
    population=["catheter-related bladder discomfort"],
    intervention=["duloxetine"],
    comparison=["placebo"],
    outcome=["catheter-related bladder discomfort incidence"],
)

query = QueryGenerator().generate(
    population=pico.population,
    intervention=pico.intervention,
)
candidates = QuestionStudySearcher(
    index_path="data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl"
).search_from_query_output(query, top_k=3).studies

result = asyncio.run(
    Module3AnalysisRunner(MockLLMGateway()).run(
        question=question,
        pico=pico,
        eligibility_criteria=EligibilityCriteria(inclusion=[], exclusion=[], confidence="low"),
        preliminary_plan=PreliminaryAnalysisPlan(
            primary_outcome="catheter-related bladder discomfort incidence",
            effect_measures={"binary": "RR", "continuous": "MD"},
            confidence="low",
        ),
        candidates=candidates,
    )
)

print(len(result.screening.included))
print(result.aggregation.analyses[0].pooled_result)
print(result.grade.assessments[0].certainty)
```

## 常见问题

### 1. CLI 输出为空或 included 为 0

当前 `--mock` CLI 在本地索引无命中时会自动注入 synthetic candidate，因此正常情况下不应为空。若你绕过 CLI 直接调用 runner，候选为空通常是本地索引没有命中。优先使用上面的度洛西汀示例，并显式传入：

```bash
--population "catheter-related bladder discomfort" --intervention "duloxetine"
```

如果索引文件不存在，先运行：

```bash
python -m ebm_backend.index_construction.interfaces.cli index-derived --data-root data/data_for_test/data_demo_with_mesh
```

### 2. 为什么 mock extraction 给不同研究相同事件数？

这是 CLI smoke 的 deterministic mock 行为，只用于验证流程和 aggregation 接口。真实数据抽取由 `DataExtractor` 通过 `LLMGateway` 调用 `data_extraction` prompt/schema，后续接真实 LLM 后会按 article evidence context 输出。

如果你要验证多篇 RCT 的不同抽取值，请跑：

```bash
pytest tests/unit/test_module3_analysis.py::test_module3_synthetic_rcts_full_flow_through_llm_gateway -q
```

这个测试造了 3 篇不同事件数的 synthetic RCT，并通过真实 `LLMGateway` 类完成 structured output 解析。

如果要验证真实外部 LLM，请跑 integration smoke：

```bash
RUN_REAL_LLM=1 pytest \
  tests/integration/test_module3_real_llm_smoke.py::test_module3_real_llm_extraction_only_synthetic_rcts \
  -q -s
```

### 3. 为什么 CLI 目前必须 `--mock`？

为了避免手动测试时误调用真实 API。真实 LLM 路径已经在各 stage 中使用 `LLMGateway.call(..., cacheable=False)` 预留；正式开放 CLI 真实路径前，需要先补真实 API smoke、错误重试和成本提示。

### 4. 当前是否使用 CacheManager？

不使用。Module 3 简化版所有 LLM 调用统一 `cacheable=False`，且 runner 不需要 sqlite connection。

## 当前限制

- 不接数据库，不保存 run 状态。
- 不实现 cache、usage tracking。
- 不做统计派生；extraction 只抽原文可见数值。
- Aggregation 目前只把已抽取完整字段转成 `StudyData` 并调用 `StatsEngine`。
- Selective reporting 固定 `unable_to_determine`，不查 protocol/registry。
- Publication bias 暂未做外部判断。
- CLI 仅开放 `--mock` 路径。
