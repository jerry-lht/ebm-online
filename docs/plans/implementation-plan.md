# Online EBM Pipeline — 实现计划

## Context

本项目是一个自动化循证医学 (EBM) pipeline，从用户输入的临床问题出发，自动完成文献检索、筛选、数据抽取、Meta 分析和 GRADE 评估。当前状态：Phase 0 与 Phase 1 已完成，`src/` 中已具备共享基础设施骨架，`data/pmc-rct/` 已有 2023-2026 年的 PMC RCT 数据。

---

## 实现阶段总览

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 项目骨架 & 基础设施 | ✅ 完成 |
| Phase 1 | Shared Infrastructure (LLM Gateway + Stats Engine) | ✅ 完成 |
| Phase 2 | Module 1: Index Construction (离线, 100篇) | ✅ 简化版完成 |
| Phase 3 | Module 2: Question-to-Study (在线) | ✅ 简化版完成（无 SQL LLM 链路） |
| Phase 4 | Module 3: EBM Annotation and Analysis (在线) | ✅ 简化版完成（mock LLM 闭环） |
| Phase 5 | Pipeline Orchestrator & API | ✅ 简化版完成（同步内存态 + FastAPI trace） |
| Phase 6 | Frontend (Gradio Demo) | ✅ 轻量 demo 完成 |
| Phase 7 | 集成测试 & 端到端验证 | 未开始 |

---

## Phase 0: 项目骨架 & 基础设施搭建

**目标：** 建立项目目录结构、依赖管理、配置系统、Docker 编排、数据库 schema。

### 任务清单

1. **创建项目目录结构**（按 architecture/architecture-design.md §8 的定义）
   ```
   ebm-online/
   ├── config/
   │   ├── settings.py          # Pydantic Settings
   │   └── .gitkeep             # 仅保留配置代码，不放环境文件
   ├── src/
   │   ├── __init__.py
   │   ├── orchestrator/
   │   ├── modules/
   │   │   ├── index/           # Module 1
   │   │   ├── question/        # Module 2
   │   │   └── analysis/        # Module 3
   │   ├── llm/
   │   │   ├── prompts/
   │   │   └── schemas/
   │   ├── stats/
   │   ├── storage/
   │   └── api/
   ├── frontend/
   ├── tests/
   └── requirements.txt
   ```

2. **配置系统** (`config/settings.py`)
   - 使用 Pydantic Settings
   - 环境变量：`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ES_HOST`, `REDIS_URL`, `DATABASE_URL`
   - 模型配置：model name, temperature, pricing

3. **数据库初始化** (`src/storage/db.py`, `src/storage/models.py`)
   - SQLite 连接管理
   - 表结构：`pipeline_runs`, `llm_cache`, `llm_usage`
   - Migration 脚本

4. **requirements.txt**
   - fastapi, uvicorn
   - openai, pydantic, pydantic-settings
   - elasticsearch, httpx
   - numpy, scipy
   - gradio
   - pytest

### 验证方式
- `python -c "from ebm_backend.shared.config.settings import settings; print(settings)"` 正常输出
- SQLite 表创建成功

---

## Phase 1: Shared Infrastructure

**目标：** 实现 LLM Gateway（简化版，无限流/重试）和 Stats Engine。

### 1.1 LLM Gateway (`src/llm/gateway.py`)

**任务：**
1. 实现 `LLMGateway` 类，接口如 architecture/shared-infrastructure-design.md §2.2
2. 使用 OpenAI SDK，支持 structured output (response_format)
3. 内部流程：Cache check → API call → Parse → Cache save → Track usage

### 1.2 Cache Layer (`src/llm/cache.py`)

**任务：**
1. 实现 `CacheManager` 类
2. Cache key 生成：`hash(task_type + inputs + prompt_version)`
3. 只缓存 screening / extraction / rob 三种任务
4. SQLite 存储，表结构如 architecture/shared-infrastructure-design.md §3.5
5. 失效 API：按 study / prompt_version / run 失效

### 1.3 Rate Limiter & Retry（暂不实现）

> **决策：** 初期使用简单的 OpenAI SDK 直接调用，不做限流和重试。后续根据实际使用情况再扩展。
> 如遇到 rate limit 或超时，手动重跑即可。

### 1.4 Token & Cost Tracker (`src/llm/tracker.py`)

**任务：**
1. 每次调用记录：call_id, run_id, module, task_name, tokens, cost, latency
2. 费用计算（`src/llm/pricing.py`）
3. 聚合查询：run-level, module-level, task-level

### 1.5 Stats Engine (`src/stats/`)

**任务：**
1. `src/stats/effects.py` — 单 study effect size 计算
   - MD, SMD (Hedges' g), log RR, log OR, Generic IV
2. `src/stats/pooling.py` — Pooling methods
   - Fixed: IV, MH, Peto
   - Random: DerSimonian-Laird
3. `src/stats/heterogeneity.py` — 异质性检验
   - Cochran's Q, I², τ²
4. `src/stats/derivation.py` — 统计转换
   - CI→SD, SE→SD, p→SE, median/IQR→mean/SD
5. `src/stats/corrections.py` — Zero-cell correction
6. `src/stats/engine.py` — StatsEngine 主类，整合上述模块

### 验证方式
- LLM Gateway：mock OpenAI API，验证 cache hit/miss
- Stats Engine：用 Cochrane data-rows 的已知数据验证 pooled effect 数值正确性
- 单元测试覆盖所有统计公式

### Phase 1 完成记录

- `LLMGateway` 已实现基础调用链：cache check → OpenAI call → parse → cache save → usage record
- `CacheManager` 已实现 `screening / extraction / rob` 三类缓存与失效接口
- `UsageTracker` 已实现调用记录、计费与 run/module 聚合查询
- `StatsEngine` 已实现 effect size、pooling、heterogeneity、derivation、zero-cell correction
- `tests/unit` 已补充对应回归测试

---

## Phase 2: Module 1 — Index Construction (离线，小样本验证)

**目标：** 先交付一个可运行的“简化版 Module 1”闭环：整理 demo `primary_rct` 数据集，完成 PI Extraction、PI Normalization / MeSH 映射、本地轻量索引和检索测试。100 篇与 1000 篇 demo 闭环均已完成；真实 Batch API 和真实 Elasticsearch 降级为后续扩展项。

### 当前实现状态

**已完成：**
- `data/pmc-rct/manifest/files.jsonl` 的 `primary_rct` 读取与前 100 篇样本选择
- demo 数据统一整理到 `data/data_for_test/`，包括 `data_demo/`、`data_demo_with_mesh/` 和 `data_demo_1000/`
- `select-demo` 支持从 `data/pmc-rct` 主题簇优先选择 1000 篇 `primary_rct`
- `title + abstract` 解析与 study 级别对象封装
- PI 抽取 prompt/schema 文件
- 单篇 demo runner：真实 OpenAI-compatible Chat Completions PI 抽取、span 校验、PostgreSQL 状态落库、派生 JSON 导出
- Module 1 batch runner：前 100 篇样本的 batch 请求构造、提交、轮询、output file 解析、`module1_studies` / `module1_batches` 回写
- batch 断点恢复：存在 active batch 时优先回收，默认跳过 `extraction_status = completed` 的 study
- PI 清洗、span 去重、概念拆分、NLM MeSH Lookup 在线查询、短语候选映射、本地兜底 MeSH 映射、同义词扩展、indexable_text 生成
- PI-first demo export：`pi -> extraction -> normalized -> document -> study`
- ES 索引 mapping、字段结构和文档组装
- 简化版 Module 1 runner 支持 `pi_mode=llm|local`：默认走真实 LLM，`local` 用于先调通数据复制、PI 归一化、PMID 回填 MeSH 入索引和本地检索验证链路
- CLI 入口：`python -m ebm_backend.index_construction.interfaces.cli simplified --pi-mode local|llm`
- 1000 篇选样入口：`python -m ebm_backend.index_construction.interfaces.cli select-demo --source-data-root data/pmc-rct --dest-data-root data/data_for_test/data_demo_1000 --total 1000`
- 已有 derived 结果可直接重建索引：`python -m ebm_backend.index_construction.interfaces.cli index-derived --data-root data/data_for_test/data_demo_with_mesh`
- 自定义 query 检索入口：`python -m ebm_backend.index_construction.interfaces.cli search-local --query "..." --top-k 3`
- `data/data_for_test/data_demo_with_mesh/derived` 当前已有 100 个 PI-first JSON，可全部重建到对应本地索引
- `data/data_for_test/data_demo_1000` 已完成 1000 篇 PI 抽取、映射、本地索引构建和检索 smoke test
- 固定 5 条 query 检索验证已通过，检索输出包含 `study_id`、`score`、`matched_fields`、`title`、`population`、`intervention`、MeSH 字段和 `article_path`
- 单元测试覆盖 loader / normalization / dedupe / MeSH fallback / index document / demo export / batch request / batch recovery / batch store writeback

**当前验收路径：**
- 重新整理 100 篇样本到 `data/data_for_test/data_demo_with_mesh/`，或整理 1000 篇主题簇样本到 `data/data_for_test/data_demo_1000/`
- 逐篇 PI 抽取与标准化/MeSH 映射；`data_demo` 的 `metadata.mesh_term` 已由 PMID 回填，构建索引时进入 `IndexDocument.mesh_terms`
- 从 `derived/*.json` 直接重建本地轻量索引
- 使用固定 query 与自定义 query 检查检索和检索后输出

**测试文档：**
- 详见 `docs/guides/phase2-demo-test-guide.md`
- 快速重建索引：
  ```bash
  python -m ebm_backend.index_construction.interfaces.cli index-derived --data-root data/data_for_test/data_demo_with_mesh
  ```
- 查看检索后输出：
  ```bash
  python -m ebm_backend.index_construction.interfaces.cli search-local \
    --index-path data/data_for_test/data_demo_1000/index/local_rct_index.jsonl \
    --query "duloxetine catheter-related bladder discomfort" \
    --top-k 3
  ```

**后续扩展：**
- 真实 OpenAI-compatible Batch API 网络验收
- 失败 batch 的自动重提策略
- 真实 Elasticsearch bulk 写入
- `module1_studies` 到检索索引的完整增量更新链路

### 2.1 PI Extraction (`src/modules/index/extraction.py`)

**任务：**
1. 读取 `data/pmc-rct/manifest/files.jsonl`，筛选 `classification=primary_rct`
2. 按 manifest 现有顺序取前 100 篇作为验证样本
3. 解析每篇 JSON 的 `metadata` 和 `sections`，优先使用 `title + abstract`
4. 构建 prompt（从 title + abstract 提取 P 和 I 的 span）
5. 编写 prompt 模板 (`src/llm/prompts/pi_extraction.txt`)
6. 编写 JSON schema (`src/llm/schemas/pi_extraction.json`)
7. 当前简化版优先逐篇执行；真实 Batch API 作为后续扩展
8. 输出验证：P/I 非空、span 可定位
9. 结果持久化到 `module1_studies` / `module1_batches`
10. 断点续跑支持

**当前代码状态：**
- 已完成：样本读取、抽取框架、真实单篇 Chat Completions smoke 入口、结果校验、状态落库、batch 请求构造、批次级状态恢复
- 简化版已完成：支持 `pi_mode=llm|local`，支持 16 worker 并发跑 PI；LLM 输出不合格时可本地 PI 兜底，避免阻塞索引闭环
- 后续扩展：提升 LLM PI 质量、真实网络环境验收与自动失败重提

### 2.2 PI Normalization (`src/modules/index/normalization.py`)

**任务：**
1. Cleaning：HTML 去除、编码统一、多 span 合并
2. Concept Extraction：规则拆分复合描述
3. MeSH Mapping：调用 NLM MeSH Lookup API
4. Synonym Expansion：MeSH entry terms + 缩写映射表
5. Study-level Aggregation：生成 indexable_text

**当前代码状态：**
- 已完成：HTML/编码清洗、span 去重与合并、规则拆分、同义词扩展、NLM MeSH Lookup API 在线查询、短语候选映射、兜底 MeSH 映射
- 部分完成：批量 concept 去重缓存、异常告警、entry terms 丰富度
- 未完成：batch 级缓存持久化

### 2.3 Index Building (`src/modules/index/indexing.py`)

**任务：**
1. ES index mapping 定义（`ebm_rct_index`）
2. Analyzer 配置（english_medical）
3. Bulk write（每批 1000 条）
4. 增量更新支持
5. 索引验证（文档总数、字段非空率、检索可用性）

**当前代码状态：**
- 已完成：mapping 定义、IndexDocument 组装、字段结构定义
- 简化版已完成：本地 JSONL 索引、从 derived 重建索引、固定 query 验证、自定义 query 检索输出
- 后续扩展：真实 ES bulk 写入、重跑去重策略

### 验证方式
- PI Extraction：`data/data_for_test/data_demo_with_mesh/derived/*.json` 或 `data/data_for_test/data_demo_1000/derived/*.json` 可查看每篇 PI-first 输出；LLM 质量问题暂列后续优化，不阻塞简化版索引验收
- MeSH Mapping：文章级 PMID 回填 MeSH 进入 `document.mesh_terms`；PI concept MeSH 进入 `mesh_population` / `mesh_intervention`
- Index：`python -m ebm_backend.index_construction.interfaces.cli index-derived --data-root data/data_for_test/data_demo_with_mesh`
- Search：`python -m ebm_backend.index_construction.interfaces.cli search-local --index-path data/data_for_test/data_demo_1000/index/local_rct_index.jsonl --query "postoperative pain nerve block surgery" --top-k 10`

---

## Phase 3: Module 2 — Question-to-Study (在线)

**目标：** 实现从临床问题到候选文献的完整流程。

### 3.1 Question Expansion (`backend/src/ebm_backend/online_pipeline/application/question_study/expansion.py`)

**任务：**
1. Prompt 模板 (`backend/src/ebm_backend/shared/llm/prompts/question_expansion.txt`)
2. JSON schema (`backend/src/ebm_backend/shared/llm/schemas/question_expansion.json`)
3. 输出：PICO + eligibility + preliminary analysis plan + confidence 标注
4. 错误处理：JSON 解析失败重试、非医学问题检测

### 3.2 Query Generation (`backend/src/ebm_backend/online_pipeline/application/question_study/query_gen.py`)

**任务：**
1. MeSH API 调用封装
2. 术语映射：P/I terms → MeSH preferred + entry terms
3. Boolean 组装：`(P_block) AND (I_block)`
4. Fallback：MeSH 未命中时使用原始术语

### 3.3 Index Search (`backend/src/ebm_backend/online_pipeline/application/question_study/search.py`)

**任务：**
1. ES Query DSL 构建（多字段加权）
2. Boost 配置：PI 字段 3.0, title/abstract 2.0, MeSH 1.5
3. Fallback 策略（4 级逐步放宽）
4. 结果排序和去重

### 验证方式
- Question Expansion：用 3-5 个示例问题验证输出格式和质量
- Query Generation：验证 MeSH 映射和 Boolean 语法
- Index Search：用已知问题验证召回率

---

## Phase 4: Module 3 — EBM Annotation and Analysis (在线)

**目标：** 实现最复杂的模块，包含 6 个子步骤。

### 当前实现状态

**已完成简化版：**
- `backend/src/ebm_backend/online_pipeline/application/evidence_analysis/models.py`：补齐 Module 3 数据结构，包括 screening、planning、evidence context、extraction row、RoB、aggregation、GRADE、runner 总结果
- `StudyScreener`：逐篇候选文献调用 `LLMGateway` structured output；失败时默认纳入并记录 warning
- `AnalysisPlanner`：一次性调用 LLM 生成 `AnalysisSpec`；失败时基于 PICO / preliminary plan 生成 fallback
- `EvidenceContextBuilder`：读取 `article_path` 对应 derived article JSON，抽取 abstract / methods / results / tables；无全文时使用 candidate title/abstract
- `DataExtractor`：按 `study x analysis` 调 LLM，抽取原文可见数值和 evidence spans；不做统计推导
- `RiskOfBiasAssessor`：逐篇调用 LLM 判断 RoB 1 可判断域；`selective_reporting` 固定补 `unable_to_determine`
- `MetaAnalysisAggregator`：不调用 LLM，把完整 extracted rows 转成 `StudyData`，使用现有 `StatsEngine` 计算 study effects、pooled result 和 heterogeneity；数据不足时进入 excluded rows
- `GradeAssessor`：每条 analysis 调 LLM，基于 aggregation / RoB / missing rows 输出 certainty 和 downgrade reasons
- `Module3AnalysisRunner`：串起 screening → planning → evidence → extraction → RoB → aggregation → GRADE
- `ebm_backend.online_pipeline.interfaces.cli.evidence_analysis --mock`：本地检索 + deterministic mock LLM 输出，可跑通完整 Module 3 JSON 输出
- Prompt/schema 已新增：`study_screening`、`analysis_planning`、`data_extraction`、`risk_of_bias`、`grade_assessment`
- 单元测试已新增：`tests/unit/test_module3_analysis.py`

**当前约束：**
- 所有 LLM 调用统一 `cacheable=False`
- 不接数据库，不记录 run 状态
- 不实现缓存，不使用 `CacheManager`
- 不记录 usage tracking
- CLI 目前只开放 `--mock`，避免手动测试误打真实 API

**测试文档：**
- 详见 `docs/guides/module3-test-guide.md`

### 4.1 Study Screening (`backend/src/ebm_backend/online_pipeline/application/evidence_analysis/screening.py`)

**任务：**
1. Prompt 模板 (`backend/src/ebm_backend/shared/llm/prompts/study_screening.txt`)
2. JSON schema (`backend/src/ebm_backend/shared/llm/schemas/study_screening.json`)
3. 逐篇调用，输出 include/exclude + rationale
4. 简化版不缓存，统一 `cacheable=False`

### 4.2 Analysis Planning (`backend/src/ebm_backend/online_pipeline/application/evidence_analysis/planning.py`)

**任务：**
1. Prompt 模板 (`backend/src/ebm_backend/shared/llm/prompts/analysis_planning.txt`)
2. 输入：preliminary plan + included studies summaries
3. 输出：confirmed_analysis_list（含 analysis_id 生成逻辑）
4. Validation：outcome_type 与 effect_measure 一致性

### 4.3 Data Extraction (`backend/src/ebm_backend/online_pipeline/application/evidence_analysis/extraction.py`)

**任务：**
1. Evidence Localization：从全文提取 abstract + results + tables
2. Prompt 模板 (`backend/src/ebm_backend/shared/llm/prompts/data_extraction.txt`)
3. JSON schema (`backend/src/ebm_backend/shared/llm/schemas/data_extraction.json`)
4. Per-study × per-analysis 调用
5. 数值合理性校验
6. 简化版不缓存，统一 `cacheable=False`

### 4.4 Risk of Bias (`backend/src/ebm_backend/online_pipeline/application/evidence_analysis/rob.py`)

**任务：**
1. Evidence Localization：从全文提取 abstract + methods
2. Prompt 模板 (`backend/src/ebm_backend/shared/llm/prompts/risk_of_bias.txt`)
3. JSON schema (`backend/src/ebm_backend/shared/llm/schemas/risk_of_bias.json`)
4. 5 域 LLM 评估 + Selective reporting 系统填充
5. overall_rob 规则计算
6. 简化版不缓存，统一 `cacheable=False`

### 4.5 Meta-analysis Aggregation (`backend/src/ebm_backend/online_pipeline/application/evidence_analysis/aggregation.py`)

**任务：**
1. Row Alignment：comparison/outcome/direction/unit 一致性检查
2. Statistical Derivation：调用 Stats Engine 的 derivation 模块
3. Single-study Effect 计算：调用 Stats Engine
4. Pooling：调用 Stats Engine（自动选择 method + model）
5. Heterogeneity 计算
6. 输出 AggregationResult

### 4.6 GRADE Assessment (`backend/src/ebm_backend/online_pipeline/application/evidence_analysis/grade.py`)

**任务：**
1. Prompt 模板 (`backend/src/ebm_backend/shared/llm/prompts/grade_assessment.txt`)
2. JSON schema (`backend/src/ebm_backend/shared/llm/schemas/grade_assessment.json`)
3. 五域判断：
   - Risk of bias：规则（high-RoB 占比）
   - Inconsistency：规则（I², Q p-value）
   - Indirectness：LLM（PICO 对齐）
   - Imprecision：LLM（CI + MID 判断）
   - Publication bias：固定 unable_to_determine
4. Overall certainty 计算（High → 逐级降）

### 验证方式
- Screening：用 mock 数据验证 include/exclude 逻辑
- Aggregation：用 mock extraction 输出验证 `StatsEngine` study effect / pooled result / excluded rows
- 端到端：`Module3AnalysisRunner` mock LLM 单元测试，以及 `python -m ebm_backend.online_pipeline.interfaces.cli.evidence_analysis --mock ...`
- 当前命令：
  ```bash
  pytest tests/unit/test_module3_analysis.py -q
  pytest tests/unit/test_module2_question.py tests/unit/test_stats_engine.py tests/unit/test_module3_analysis.py -q
  python -m ebm_backend.online_pipeline.interfaces.cli.evidence_analysis \
    --mock \
    --question "Does duloxetine reduce catheter-related bladder discomfort?" \
    --population "catheter-related bladder discomfort" \
    --intervention "duloxetine" \
    --comparison "placebo" \
    --outcome "catheter-related bladder discomfort incidence" \
    --top-k 3
  ```

---

## Phase 5: Pipeline Orchestrator & API

**目标：** 实现基于 1000 篇索引的真实简化闭环：question -> Module 2 -> 1000 篇本地检索 -> Module 3 -> trace/results API。

### 当前实现状态

**已完成 1000 篇索引真实简化闭环：**
- `backend/src/ebm_backend/online_pipeline/infrastructure/pipeline_repository.py`：进程内 `InMemoryPipelineStore`、`PipelineRunState`、`PipelineStepTrace`，状态支持 `pending -> running -> completed/failed`
- `backend/src/ebm_backend/online_pipeline/application/run_pipeline.py`：同步 `PipelineOrchestrator`，按 `question_expansion -> question_pi_extraction -> query_generation -> local_search -> module3_analysis` 执行
- 默认 `use_mock=false`：真实 LLM 执行 question expansion、PI extraction、query generation、screening、planning、extraction、RoB、GRADE
- `SimplifiedPipelineMockGateway`：覆盖 Module 2 / Module 3 所需 structured-output task，保留给 `use_mock=true` smoke test
- `backend/src/ebm_backend/online_pipeline/interfaces/api/main.py`：FastAPI app 初始化与 `/health`
- `backend/src/ebm_backend/online_pipeline/interfaces/api/routes_pipeline.py`：`POST /pipeline/runs`、`GET /pipeline/runs`、`GET /pipeline/runs/{run_id}`、`GET /pipeline/runs/{run_id}/trace`、`GET /pipeline/runs/{run_id}/results`
- Trace payload 可查看 PICO、PI、Boolean query、本地检索 candidates、matched fields、score、article path、fallback search、screening、planning、extraction rows、risk of bias、aggregation、GRADE
- 默认本地索引路径统一为 `data/data_for_test/data_demo_1000/index/local_rct_index.jsonl`
- 真实模式下无检索结果时不注入 synthetic candidate；mock 模式保留 synthetic candidate smoke 兜底
- `/results` 返回 `candidates`、`screening`、`planning`、`extraction`、`risk_of_bias`、`aggregation`、`grade`、`warnings`
- 新增单元测试：`tests/unit/test_phase5_orchestrator.py`、`tests/unit/test_phase5_api.py`

**当前约束：**
- API 创建 run 立即返回 `pending run_id`，后台任务在同进程内继续执行
- run 状态仅保存在进程内，服务重启后丢失
- 不接数据库、不使用 Redis/Celery、不实现 cache/usage tracking
- 不实现 WebSocket、暂停、断点续跑或 step-level rerun
- 真实模式需要可用 OpenAI-compatible API key；默认只分析 top 5 candidates 控制调用量

**测试文档：**
- 详见 `docs/guides/phase5-api-test-guide.md`

### 5.1 Pipeline Orchestrator (`src/orchestrator/`)

**任务：**
1. `pipeline.py` — DAG 定义（模块间依赖关系）✅ 简化版完成
2. `state.py` — 状态管理（pending → running → completed/failed）✅ 简化版完成
3. 后台任务队列接入（后续扩展）
4. 断点续跑：从失败模块重新开始（后续扩展）
5. WebSocket 进度推送（后续扩展）

### 5.2 FastAPI Backend (`src/api/`)

**任务：**
1. `main.py` — FastAPI app 初始化 ✅ 完成
2. `routes/pipeline.py` — Pipeline 创建/查询/trace/results API ✅ 简化版完成
3. `routes/results.py` — 独立结果查询 API（当前合并在 `routes/pipeline.py` 的 `/results`）
4. `routes/usage.py` — Token/Cost 查询 API（后续扩展）
5. 实时进度推送接口（后续扩展）

### 验证方式
- API：启动 uvicorn，通过 Swagger UI 或 curl 测试各端点
- Orchestrator：提交一个问题，验证 pipeline 状态流转和 trace payload
- 自动化测试：
  ```bash
  pytest tests/unit/test_phase5_orchestrator.py tests/unit/test_phase5_api.py -q
  pytest tests/unit/test_module2_question.py tests/unit/test_module2_llm.py tests/unit/test_module3_analysis.py tests/unit/test_phase5_orchestrator.py tests/unit/test_phase5_api.py -q
  ```
- 手动启动：
  ```bash
  uvicorn ebm_backend.online_pipeline.interfaces.api.main:app --reload --host 0.0.0.0 --port 8000
  ```

---

## Phase 6: Frontend (Gradio Demo)

**目标：** 先实现一个轻量 Gradio demo，用户像使用模型对话界面一样输入 clinical question，并在同一页查看 Phase 5 pipeline 的中间过程和结果。复杂多页前端作为后续扩展，不作为当前 demo 的首要交付。

### 任务清单

1. `frontend/gradio_app.py` — Gradio Blocks 单页入口 ✅
2. 输入区：clinical question、demo question、`top_k`、`use_mock`、本地索引路径 ✅
3. 主展示区：ChatGPT-like 回答、run status、run_id、耗时、候选数量 ✅
4. Pipeline timeline：展示 `question_expansion -> question_pi_extraction -> query_generation -> local_search -> module3_analysis` ✅
5. 结构化详情：PICO、eligibility、analysis plan、PI extraction、Boolean query、local retrieval query_text、candidate studies、screening、extraction、RoB、aggregation/GRADE ✅
6. Trace：完整 JSON 查看和下载 ✅
7. 后续扩展：流式逐步刷新、历史持久化、登录、多用户隔离、复杂图表、更完整的前端形态

### 验证方式
- `python frontend/gradio_app.py --host 127.0.0.1 --port 7860` 启动成功
- `pytest tests/unit/test_phase6_gradio_app.py -q` 通过
- 提交问题 → 查看主回答、timeline、各阶段结构化详情、trace JSON 下载

---

## Phase 7: 集成测试 & 端到端验证

**目标：** 确保系统端到端可用。

### 任务清单

1. Stats Engine regression test（Cochrane data-rows，445 个 review）
2. PI Extraction benchmark（EBM-NLP，4993 篇）
3. Question Expansion benchmark（Q2CRBench-3，99 条）
4. Study Screening benchmark（Q2CRBench-3 Screened_Records）
5. 端到端测试：选 3-5 个代表性临床问题完整运行
6. 性能测试：单次 pipeline 耗时和成本统计

---

## 建议执行顺序

```
Phase 0 → Phase 1.5 (Stats Engine) → Phase 1.1-1.4 (LLM Gateway 简化版)
       → Phase 2 (Module 1, 100篇) → Phase 3 (Module 2)
       → Phase 4 (Module 3) → Phase 5 (Orchestrator + API)
       → Phase 6 (Frontend) → Phase 7 (Testing)
```

**理由：**
- Stats Engine 是纯计算模块，无外部依赖，可以最先实现并用 Cochrane 数据验证
- LLM Gateway 简化版（无 rate limiter/retry）是所有 LLM 调用的基础
- Module 1 先跑 100 篇验证流程，确认无误后再扩展全量
- Orchestrator 和 Frontend 在业务逻辑完成后再搭建

---

## 每次对话的使用方式

每次新对话时，告诉 Claude：
1. 当前要执行哪个 Phase 的哪个子任务
2. 指向本计划文档和相关设计文档作为上下文
3. 完成后运行验证步骤确认正确性

示例 prompt：
> "请执行 Phase 1.5 Stats Engine 的实现。参考 docs/architecture/shared-infrastructure-design.md §6 和 docs/plans/implementation-plan.md。完成后用 Cochrane data-rows 做 regression test。"

---

## 进度记录

> 后续每完成一个 Phase，在此处更新状态和备注。

| 日期 | 完成内容 | 备注 |
|------|----------|------|
| 2026-05-08 | Phase 0: 项目骨架 & 基础设施搭建 | 全部完成并验证通过。PostgreSQL/Redis/ES 直接安装（非 Docker），8 个测试全部 PASSED。 |
| 2026-05-08 | Phase 1: Shared Infrastructure | LLM Gateway、Cache、Usage Tracker、Stats Engine 完成，`pytest tests/unit -q` 通过。 |
| 2026-05-08 | Phase 2: Module 1 基础实现 | 完成数据加载、PI 抽取/归一化/索引文档骨架、SQLite 状态表、Batch API 预留、相关文档与测试同步；真实 batch、MeSH 在线映射、ES bulk 写入与端到端验证仍待完成。 |
| 2026-05-09 | Phase 2 环境连通性 | 根目录 `.env`、PostgreSQL、OpenAI Responses API、Elasticsearch 基础连通性已检查；本地已对齐到可用的 OpenAI-compatible 端点，并完成真实 `responses.create()` smoke test。 |
| 2026-05-09 | Phase 2 demo 数据集 | 从 `data/pmc-rct` 抽取前 100 篇 `primary_rct` 到 `data_demo/`，并将 `PMCReader` 默认入口切换到 demo 数据目录，后续 Phase 2 验证优先在该子集上跑通。 |
| 2026-05-09 | Phase 2 demo smoke | 已补齐单篇 demo runner，使用 PostgreSQL 记录 module1 状态，支持真实 LLM smoke、MeSH 在线映射和派生结果导出；下一步是在 `data_demo` 上接 100 篇 batch。 |
| 2026-05-09 | Phase 2 demo 链路整理 | 单篇 demo 已串起 PI Extraction → PI Normalization → MeSH/Synonym expansion → IndexDocument → PI-first export；已补 span/MeSH 去重和 MeSH 短语候选兜底。未完成项集中在 100 篇真实 Batch API、失败重提/恢复、真实 ES bulk 写入和检索验证。 |
| 2026-05-09 | Phase 2.1 batch 闭环 | 已补齐 Module 1 batch runner、`module1_batches` / `module1_studies` 回写、active batch 恢复、completed study 跳过，以及 fake gateway 单元测试；待办集中在真实 Batch API 网络验收、自动失败重提、ES bulk 与检索验证。 |
| 2026-05-10 | Phase 2 路线简化 | 当前交付目标改为“简化版 Module 1”：`data_demo_with_mesh/` 100 篇样本、逐篇 PI 抽取与映射、本地轻量索引和检索测试；真实 Batch API 与真实 Elasticsearch 降级为后续扩展项。 |
| 2026-05-10 | Phase 2 简化 runner 调通入口 | `Module1SimplifiedRunner` 增加 `pi_mode=llm|local`，新增 `python -m ebm_backend.index_construction.interfaces.cli simplified` 命令入口；确认 `data_demo` 中 PMID 回填的 `metadata.mesh_term` 会写入本地索引的 `mesh_terms` 字段。 |
| 2026-05-10 | Phase 2 本地索引验证 | 新增 `index-derived` 快速入口，可跳过 LLM/数据库，直接从 `data_demo_with_mesh/derived` 重建 `local_rct_index.jsonl`；当前 100 个 derived 全部入索引，5 条固定 query 检索验证 5/5 通过。 |
| 2026-05-10 | Phase 2 检索输出验收 | 新增 `search-local` 自定义 query 检索入口；`docs/guides/phase2-demo-test-guide.md` 已记录 6 条基于现有文章的测试 query、预期 top hit 与检索输出字段。至此 Module 1 简化版闭环完成，后续进入 Phase 3 前可继续优化 PI 质量和排序策略。 |
| 2026-05-10 | Phase 2 1000 篇 demo 验收 | demo 数据统一移动到 `data/data_for_test/`；新增 `select-demo` 主题簇选样入口并生成 `data/data_for_test/data_demo_1000`；已完成 1000 篇 PI 抽取、离线 MeSH fallback 映射、本地索引构建和检索 smoke test。`postoperative pain nerve block surgery` Top1=`pmid:37360747`。 |
| 2026-05-10 | Phase 3: Module 2 简化实现 | 已完成 `backend/src/ebm_backend/online_pipeline/application/question_study` 下 `expansion/query_gen/search` 的最小闭环实现：PICO 结构化骨架、离线 MeSH fallback 的 P/I 查询组装、基于 `LocalRCTIndex` 的候选文献检索，并新增 `tests/unit/test_module2_question.py`（3/3 通过）。曾发现 `test_index_document_contains_core_fields` 将 PI 归一化 MeSH 误期望在 `mesh_terms`；已改为合并 `mesh_terms` + `mesh_population` + `mesh_intervention` 断言。 |
| 2026-05-10 | Phase 3: Module 2 接 LLM | `LLMGateway` 支持 `conn=None`，在线链路不再依赖 SQL；`QuestionExpander.expand_with_llm`、`QuestionPIExtractor.extract_with_llm`、`QueryGenerator.generate_with_llm` 分别实现问题扩展、PI 提取、MeSH-like preferred/entry terms 扩展与 Boolean 组装；新增 `Module2LLMRunner` 返回可传给下游的 `Module2LLMResult`；`LLMGateway` 支持 Responses API，并在兼容端点缺少 `/responses` 时降级到 Chat Completions；Mock 单测见 `tests/unit/test_module2_llm.py`。 |
| 2026-05-10 | Phase 3 简化版验收与测试文档更新 | 已补充 `docs/guides/module2-test-guide.md`：无 SQL 运行方式（`LLMGateway(conn=None)`）、端到端 `Module2LLMRunner` 可执行示例、与当前 100 篇索引匹配的示范问题；新增稳定检索回归用例 `test_clinical_question_retrieval_ranks_duloxetine_catheter_trial_first`（Top1=`pmid:37877838`）；`pytest tests/unit/test_llm_infra.py tests/unit/test_module2_llm.py tests/unit/test_module2_question.py -q` 通过（12/12）。 |
| 2026-05-10 | Phase 4: Module 3 简化闭环 | 已完成 `backend/src/ebm_backend/online_pipeline/application/evidence_analysis` 下 screening、planning、evidence context、extraction、RoB、aggregation、GRADE、runner 与 mock CLI；所有 LLM 调用统一 `cacheable=False`，不接数据库/缓存/usage；新增 prompts/schemas 和 `tests/unit/test_module3_analysis.py`；`pytest tests/unit/test_module3_analysis.py -q` 与 Module2+Stats+Module3 联合回归通过。 |
| 2026-05-10 | Phase 4 测试文档更新 | 新增 `docs/guides/module3-test-guide.md`，记录 Module 3 简化版自动化测试、mock CLI 手动测试、Python runner 联调、预期输出字段和常见问题；README 与 docs 索引已补充 Module 3 测试入口。 |
| 2026-05-10 | Phase 5: Orchestrator/API 简化闭环 | 已完成同步 `PipelineOrchestrator`、进程内 run/step state、Phase 5 mock gateway、FastAPI `/pipeline/runs`、`/trace`、`/results`；默认 `use_mock=true`，不依赖数据库/Redis/Celery/cache/usage。`pytest tests/unit/test_phase5_orchestrator.py tests/unit/test_phase5_api.py -q` 通过（3/3），Module2+Module3+Phase5 联合回归通过（21/21）。 |
| 2026-05-10 | Phase 5 测试文档更新 | 新增 `docs/guides/phase5-api-test-guide.md`，记录 API 启动、curl 示例、trace 字段、自动化测试、真实 LLM 使用方式和当前限制；README 与 docs 索引已补充 Phase 5 测试入口。 |
| 2026-05-10 | Phase 5: 1000 篇索引真实简化闭环 | 默认索引切换到 `data/data_for_test/data_demo_1000/index/local_rct_index.jsonl`，API 默认 `use_mock=false`；真实模式无命中不再注入 synthetic candidate；trace/results 增加 matched fields、fallback search、risk_of_bias 和 demo-aware 推荐问题说明。`pytest tests/unit/test_module2_question.py tests/unit/test_module2_llm.py tests/unit/test_module3_analysis.py tests/unit/test_phase5_orchestrator.py tests/unit/test_phase5_api.py -q` 通过（24/24）。 |
| 2026-05-10 | Phase 5: staged 真实 LLM 全流程验收 | 新增 `RUN_REAL_LLM_FULL=1` opt-in integration test，可实时打印 question expansion、PI、query、local search、screening、planning、extraction、RoB、aggregation、GRADE，并保存 `/tmp/phase5_pain_block_staged_module3.json`。当前 pain-block 问题 1000 索引返回 6 篇，screening 纳入 1 篇、排除 5 篇，完整流程跑通；aggregation 为单研究效应，不是多篇合并 meta-analysis。 |
| 2026-05-10 | Phase 6: Gradio demo | 新增 `frontend/gradio_app.py`，真实模式通过 FastAPI 创建 run 并轮询 `/trace`，默认 `use_mock=false` 跑真实 LLM，`use_mock=true` 用本地 `TestClient` 做 smoke；同页展示主回答、summary、timeline、PICO/eligibility/plan、PI、query/local search、candidate studies、screening、extraction、RoB、aggregation/GRADE 和 trace JSON 下载；新增 `tests/unit/test_phase6_gradio_app.py` 与 `docs/guides/phase6-gradio-demo-guide.md`。 |
