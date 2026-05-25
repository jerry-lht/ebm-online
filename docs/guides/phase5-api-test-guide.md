# Phase 5 API 测试指南：1000 篇索引真实闭环

- **Status:** active
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** Current Phase 5 runnable API path and test procedure.


本文档用于验证 **Phase 5 Pipeline Orchestrator & API**：提交一个 clinical question 后，后端立即返回 `pending run_id`，后台执行 Module 2 与 Module 3，并把中间过程保存到进程内 trace，方便查看问题拆解、检索式生成、1000 篇本地索引检索、screening、extraction、risk of bias、aggregation 和 GRADE。

> 说明：当前 Phase 5 不接数据库、不使用 Redis/Celery、不实现 cache/usage tracking，也不提供 WebSocket。默认 `use_mock=false`，走真实 LLM + `data_demo_1000` 索引；`use_mock=true` 保留给无 API key 的 smoke test。

## Module1+2 专用检索接口（retrieval）

新增独立接口用于 Module1+2 联调，不触发 Module3：

- `POST /retrieval/run`
- 输入字段：
  - `question`（必填）
  - `mode`：`static` 或 `dynamic`（默认 `dynamic`）
  - `top_k`（默认 5）
  - `index_path`（可选）
  - `static`：使用 `index_path`（默认 `data/data_for_test/data_demo_1000/index/local_rct_index.jsonl`）
  - `dynamic`：online-first（先 PubMed 检索）；忽略传入 `index_path`
  - `enable_v2_backfill`（兼容字段；`dynamic` 模式当前忽略，始终在线流程；`static` 固定 `false`）
  - `use_mock_llm`（默认 `false`）
  - `rct_only`（默认 `true`，会在 query 上附加 RCT 过滤块）
- 输出字段：
  - `expansion`, `pi`, `query`, `search`
  - `stats`（统一统计字段）
  - `cleaned_article_choices`（动态模式仅返回 `retrieval_cache_v2/articles_cleaned/*.json`；静态模式为空）

动态模式检索策略（当前）：

1. 先在线 PubMed 检索候选（online-first）
2. 对候选逐篇检查本地是否已有 cleaned（`retrieval_cache_v2/articles_cleaned/*.json`）
3. 已有 cleaned 直接复用，不重复清洗
4. 仅对缺失 cleaned 的候选执行 `PMC XML -> cleaning -> v2 index` 入库

`stats` 统一字段定义：

- `retrieved_total`
- `returned_top_k`
- `online_backfill_used`
- `pubmed_requested`
- `rct_gate_excluded`
- `download_success`
- `clean_success`
- `ingested_success`
- `timings_ms`（毫秒，整型、非负）：
  - `question_expansion_ms`
  - `question_pi_extraction_ms`
  - `query_generation_ms`
  - `local_search_ms`
  - `total_ms`

`cleaned_article_choices` 指向的 cleaned JSON 采用严格 schema：

- 必须包含：`study_id`、`metadata`、`derived`、`xml_content`
- `xml_content.sections`: `list[{section:str, text:str}]`
- `xml_content.tables`: `list[{section_path:list[str], raw_xml:str}]`
- 不再兼容 `sections[].blocks`（legacy payload 会报错）

## 当前实现范围

已完成的简化链路：

1. `InMemoryPipelineStore`：进程内保存 `PipelineRunState`，状态支持 `pending -> running -> completed/failed`。
2. `PipelineOrchestrator`：同步执行 `question_expansion -> question_pi_extraction -> query_generation -> local_search -> module3_screening -> module3_planning -> (module3_extraction || module3_rob) -> module3_aggregation -> module3_grade -> module3_analysis`。
3. `SimplifiedPipelineMockGateway`：覆盖 Module 2 和 Module 3 所需 structured-output task，供 `use_mock=true` smoke test 使用。
4. FastAPI app：提供 run 创建、列表、状态、trace、results 查询接口。
5. FastAPI app 同时提供 `retrieval` 独立接口（只跑 Module1+2）。
5. 中间过程 trace：每个 step 保存 `status`、`summary`、`payload`、`error`、时间戳。
6. 默认索引路径统一为 `data/data_for_test/data_demo_1000/index/local_rct_index.jsonl`。
7. 真实模式下本地检索无命中时不注入 synthetic candidate；mock 模式仍可兜底生成 synthetic candidate，保证流程 smoke 可跑通。

## 相关代码路径

- `backend/src/ebm_backend/online_pipeline/infrastructure/pipeline_repository.py` — pipeline run / step 状态和内存 store
- `backend/src/ebm_backend/online_pipeline/application/run_pipeline.py` — orchestrator 与 mock gateway
- `backend/src/ebm_backend/online_pipeline/interfaces/api/main.py` — FastAPI app 入口
- `backend/src/ebm_backend/online_pipeline/interfaces/api/routes_pipeline.py` — Phase 5 API routes
- `backend/src/ebm_backend/online_pipeline/interfaces/api/routes_retrieval.py` — Module1+2 retrieval routes
- `tests/unit/test_phase5_orchestrator.py` — orchestrator trace 单元测试
- `tests/unit/test_phase5_api.py` — FastAPI route 单元测试
- `tests/unit/test_retrieval_api.py` — retrieval route 单元测试

## 依赖与前置条件

1. Python 依赖已安装：

   ```bash
   pip install -r requirements.txt
   ```

2. 推荐确认 1000 篇本地索引存在：

   ```bash
   test -f data/data_for_test/data_demo_1000/index/local_rct_index.jsonl
   ```

   若不存在，可从 derived 重建：

   ```bash
   python -m ebm_backend.index_construction.interfaces.cli index-derived \
     --data-root data/data_for_test/data_demo_1000
   ```

3. 真实模式需要 `.env` 中有可用的 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_MODEL`，并且外部 API 可访问。
4. `use_mock=true` 不需要真实 OpenAI API，不需要数据库、Redis 或 Elasticsearch。

## 1000 篇 demo-aware 推荐问题

`data/data_for_test/data_demo_1000/manifest/selection_summary.json` 的主题簇包括 surgery/anesthesia/pain、exercise/rehab、mental/neuro、diabetes/metabolic、COVID/respiratory、dental/oral/caries、pregnancy/women。优先用下面问题验收，检索量和 included 数量会比随机医学问题更稳定：

- `In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?`
- `In orthopedic surgery patients, does tranexamic acid reduce transfusion compared with no tranexamic acid?`
- `In patients with diabetes, does exercise training improve glycemic control compared with usual care?`
- `In patients with COVID-19 or respiratory disease, does rehabilitation improve functional outcomes?`
- `In dental procedures, do local anesthesia techniques reduce procedural pain compared with conventional injection?`
- `In pregnant or postpartum women, does exercise or lifestyle intervention improve maternal outcomes?`

## 自动化测试

只跑 Phase 5：

```bash
PYTHONPATH=backend/src pytest tests/unit/test_phase5_orchestrator.py tests/unit/test_phase5_api.py -q
```

预期：所有测试通过。

覆盖内容：

| 测试 | 说明 |
|------|------|
| `test_phase5_orchestrator_records_module2_and_module3_trace` | 用临时本地 JSONL 索引跑完整 orchestrator，确认 Module 2 + Module 3 分阶段 trace 都被记录，且保留 `module3_analysis` 汇总 step |
| `test_phase5_api_creates_run_and_exposes_trace` | 用 FastAPI `TestClient` 提交问题，确认 `/trace` 和 `/results` 可返回中间过程与结果 |
| `test_phase5_api_returns_404_for_unknown_run` | 不存在的 `run_id` 返回 404 |

与 Module 2 / Module 3 一起回归：

```bash
PYTHONPATH=backend/src pytest \
  tests/unit/test_module2_question.py \
  tests/unit/test_module2_llm.py \
  tests/unit/test_module3_analysis.py \
  tests/unit/test_phase5_orchestrator.py \
  tests/unit/test_phase5_api.py \
  -q
```

当前验证记录：24 个测试通过。

只跑 retrieval route：

```bash
PYTHONPATH=backend/src pytest tests/unit/test_retrieval_api.py -q
```

当前验证记录（2026-05-15）：

- `tests/unit/test_retrieval_api.py`：6 passed

真实 LLM + 1000 篇索引 integration smoke：

```bash
RUN_REAL_LLM=1 .venv/bin/python -m pytest tests/integration/test_phase5_real_pipeline_1000.py -q -s
```

该测试默认 skip，只有设置 `RUN_REAL_LLM=1` 才会真实调用外部 LLM。它使用默认 1000 篇索引和 `top_k=1` 控制调用量，并断言检索命中真实文章、没有 synthetic candidate、Module 3 screening 可返回决策。

### 2026-05-12 真实 LLM 联调记录

本轮使用 `.env` 中配置的 SiliconFlow compatible endpoint：

```text
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
```

已通过：

- Module 2 + 1000 篇索引 + screening smoke：

  ```bash
  RUN_REAL_LLM=1 PYTHONPATH=backend/src pytest \
    tests/integration/test_phase5_real_pipeline_1000.py::test_phase5_real_llm_module2_and_screening_against_1000_index \
    -q -s
  ```

  结果：`1 passed in 317.69s`。该测试真实调用 question expansion、question PI extraction、query generation 和 screening，并确认候选来自 `data/data_for_test/data_demo_1000/index/local_rct_index.jsonl`，不是 synthetic/mock candidate。

- Module 3 standalone real-LLM smoke：

  ```bash
  RUN_REAL_LLM=1 PYTHONPATH=backend/src pytest tests/integration/test_module3_real_llm_smoke.py -q -s
  ```

  结果：`2 passed in 1020.72s`。该测试使用 synthetic RCT article fixtures，但 screening、planning、extraction、RoB 和 GRADE 均走真实 LLM。

当前阻塞：

- 新增 staged bridge 测试 `test_phase5_real_llm_module2_1000_candidates_feed_module3_trace`，目标是 Module 2 从 1000 篇索引检索 `top_k=1` 后，把真实 candidate 传给 `Module3AnalysisRunner`，并保存 `/tmp/ebm_real_llm_1000_module2_module3_trace.json`。
- 该 staged 测试目前多次卡在外部 LLM structured-output 调用，错误为 `openai.APITimeoutError: Request timed out`，底层为 `httpx.ReadTimeout`。
- 失败点主要出现在 Module 2 的 `query_generation`，偶发也会出现在 `question_pi_extraction`。已将默认 `LLM_TIMEOUT_SECONDS` 从 60 秒提高到 180 秒，但 SiliconFlow/DeepSeek 端点仍可能超时。
- staged 测试已加入 query generation timeout-only fallback：如果真实 LLM query generation 超时，会记录 `query_generation_source=local_timeout_fallback` 并用 deterministic Boolean query 继续 1000-index local search；但 question expansion 和 PI extraction 仍要求真实 LLM 成功。

后续处理建议：

- 优先更换更稳定/更快的 structured-output 模型或 endpoint 后重跑 staged bridge。
- 或显式增大超时，例如 `LLM_TIMEOUT_SECONDS=300`。
- 如果目标是稳定生成 trace，可先保留 `test_phase5_real_llm_module2_and_screening_against_1000_index` 作为真实 Module 2 验收，staged bridge 仅用于人工 opt-in。

完整真实流程 trace（耗时和费用更高，适合人工验收）：

```bash
RUN_REAL_LLM_FULL=1 PHASE5_FULL_TOP_K=6 .venv/bin/python -m pytest \
  tests/integration/test_phase5_real_pipeline_1000.py::test_phase5_real_llm_full_pain_block_trace_against_1000_index \
  -q -s
```

输出会打印每个 pipeline step 的摘要，并把完整 trace 保存到：

```text
/tmp/phase5_pain_block_full_trace.json
```

如果想看到每一步实时输出，使用 staged 版本：

```bash
RUN_REAL_LLM_FULL=1 PHASE5_FULL_TOP_K=6 .venv/bin/python -m pytest \
  tests/integration/test_phase5_real_pipeline_1000.py::test_phase5_real_llm_staged_pain_block_module3_trace \
  -q -s
```

当前真实 staged 验收记录：

- 命令：`RUN_REAL_LLM_FULL=1 PHASE5_FULL_TOP_K=6 .venv/bin/python -m pytest tests/integration/test_phase5_real_pipeline_1000.py::test_phase5_real_llm_staged_pain_block_module3_trace -q -s`
- 问题：`In patients undergoing surgery, do ultrasound-guided nerve blocks or fascial plane blocks reduce postoperative pain compared with no block or standard analgesia?`
- 结果：`1 passed in 232.01s`
- Module 2：真实 LLM 完成 question expansion、PI extraction、query generation。
- Local search：1000 篇索引返回 6 篇候选。
- Module 3：真实 LLM 完成 screening、planning、extraction、risk of bias、GRADE；本地 stats 完成 aggregation。
- Screening：纳入 1 篇、排除 5 篇。当前示例完整跑通流程，但不是多篇合并 meta-analysis。
- Planning：生成 4 个 analysis。
- Extraction：3 个 analysis 有可计算数据，1 个因缺少原始均值/SD 标记 missing。
- 输出：`/tmp/phase5_pain_block_staged_module3.json`

步骤性质：

| Step | 是否 LLM |
|------|----------|
| question_expansion | 是 |
| question_pi_extraction | 是 |
| query_generation | 是 |
| local_search | 否，本地 1000 篇 JSONL 索引 |
| study_screening | 是 |
| analysis_planning | 是 |
| data_extraction | 是 |
| risk_of_bias | 是 |
| aggregation | 否，本地统计计算 |
| grade_assessment | 是 |

## 启动 API

```bash
PYTHONPATH=backend/src uvicorn ebm_backend.online_pipeline.interfaces.api.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

预期：

```json
{"status":"ok"}
```

Swagger UI：

```text
http://127.0.0.1:8000/docs
```

## API 手动测试

### 1. 提交一个 pipeline run

```bash
curl -s -X POST http://127.0.0.1:8000/pipeline/runs \
  -H "Content-Type: application/json" \
  -d '{
    "question": "In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?",
    "top_k": 5,
    "use_mock": false
  }'
```

预期返回：

```json
{
  "run_id": "...",
  "status": "pending",
  "question": "...",
  "top_k": 5,
  "use_mock": false,
  "index_path": "data/data_for_test/data_demo_1000/index/local_rct_index.jsonl",
  "step_count": 0,
  "error": null
}
```

真实模式如果本地检索无命中，不会注入 synthetic candidate；Module 3 会记录空候选下的 screening/planning/extraction/grade 结果。需要无 API key smoke 时，把 `use_mock` 改为 `true`。提交后继续轮询 `GET /pipeline/runs/<run_id>` 或 `/trace`，直到 `status` 变成 `completed` 或 `failed`。

### 2. 查看状态摘要

```bash
curl -s http://127.0.0.1:8000/pipeline/runs/<run_id>
```

重点检查：

- `status` 为 `completed`
- `steps[*].name` 依次为（共 11 个）：
  - `question_expansion`
  - `question_pi_extraction`
  - `query_generation`
  - `local_search`
  - `module3_screening`
  - `module3_planning`
  - `module3_extraction`
  - `module3_rob`
  - `module3_aggregation`
  - `module3_grade`
  - `module3_analysis`（兼容汇总）
- 每个 step 有 `summary`

### 3. 查看完整 trace

```bash
curl -s http://127.0.0.1:8000/pipeline/runs/<run_id>/trace
```

重点检查：

- `steps[0].payload.pico`：问题扩展后的 PICO
- `steps[1].payload.population` / `intervention`：检索用 PI
- `steps[2].payload.boolean_query`：Boolean 检索式
- `steps[3].payload.query_text`：Boolean query 转换后的本地检索文本
- `steps[3].payload.studies`：本地检索候选文献，每篇包含 `relevance_score`、`matched_fields`、`article_path`
- `steps[3].payload.fallback_search`：Boolean query 太窄且兜底检索被触发时的说明
- `steps[*].name=module3_screening`：纳入/排除判断
- `steps[*].name=module3_extraction`：抽取出的数值行
- `steps[*].name=module3_rob`：RoB 判断
- `steps[*].name=module3_aggregation`：meta-analysis aggregation 结果
- `steps[*].name=module3_grade`：GRADE certainty
- `steps[*].name=module3_analysis`：完整汇总 payload（兼容旧客户端）

### 4. 查看前端友好的结果摘要

```bash
curl -s http://127.0.0.1:8000/pipeline/runs/<run_id>/results
```

该接口返回精简结果，适合 Phase 6 前端先接入：

```text
candidates
screening
planning
extraction
risk_of_bias
aggregation
grade
warnings
```

## Python 手动联调

如果不启动 API，也可以直接调用 orchestrator：

```python
import asyncio

from ebm_backend.online_pipeline.application.run_pipeline import PipelineOrchestrator

async def main():
    run = await PipelineOrchestrator().run_question(
        question="In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?",
        top_k=5,
        use_mock=False,
    )
    print(run.status)
    print([step.name for step in run.steps])
    print(run.result["query"]["boolean_query"])
    print(run.result["grade"]["assessments"][0]["certainty"])

asyncio.run(main())
```

预期：

- `run.status` 为 `completed`
- step 数量为 5
- Boolean query 不为空
- `run.result["candidates"]` 来自 1000 篇本地索引

## 使用真实 LLM

真实 LLM 路径通过 API 设置：

```json
{
  "question": "In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?",
  "top_k": 5,
  "use_mock": false
}
```

要求：

- 根目录 `.env` 中有可用的 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_MODEL`
- 1000 篇本地索引存在
- 外部 API 可访问

注意：真实路径会依次调用 Module 2 和 Module 3 的多个 structured-output task，耗时和费用明显高于 mock；当前不记录 usage，也不做 retry。

## 无 API key smoke

```bash
curl -s -X POST http://127.0.0.1:8000/pipeline/runs \
  -H "Content-Type: application/json" \
  -d '{
    "question": "In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?",
    "top_k": 5,
    "use_mock": true
  }'
```

`use_mock=true` 会使用 deterministic mock LLM；如果检索没有命中，会注入 synthetic candidate，目的只是验证 API 和 trace 结构。

## 常见失败排查

- `status=failed` 且错误包含 API key：确认 `.env` 中的 OpenAI-compatible 配置可用，或改用 `use_mock=true`。
- `local_search.returned_count=0`：先换用上方推荐问题；随机领域可能不在 1000 篇主题簇里。
- `fallback_search.used=true`：说明 LLM 生成的 Boolean query 对本地轻量检索过窄，系统已用 P/I 原词和相关主题词兜底检索。
- `screening.included=[]`：检索命中不等于最终纳入，查看 `screening.decisions` 的 rationale/exclusion_reason。

## 当前限制

- API 创建 run 是同步阻塞的，不是后台任务。
- run 状态保存在进程内，服务重启后丢失。
- 不支持暂停、恢复、重跑某个 step。
- 不使用 Celery、Redis、数据库或 WebSocket。
- `use_mock=true` 的 clinical content 是 deterministic mock，仅用于流程验收。
- `use_mock=false` 依赖当前 Module 2/3 prompt、LLM 输出质量和 1000 篇索引覆盖范围；本轮验收目标是接口和流程真实跑通，不要求医学结论达到系统综述发表质量。
