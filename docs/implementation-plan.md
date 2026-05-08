# Online EBM Pipeline — 实现计划

## Context

本项目是一个自动化循证医学 (EBM) pipeline，从用户输入的临床问题出发，自动完成文献检索、筛选、数据抽取、Meta 分析和 GRADE 评估。当前状态：设计文档完备，`src/` 目录为空，`data/pmc-rct/` 已有 2023-2026 年的 PMC RCT 数据。需要从零搭建整个系统。

---

## 实现阶段总览

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 项目骨架 & 基础设施 | ✅ 完成 |
| Phase 1 | Shared Infrastructure (LLM Gateway + Stats Engine) | 未开始 |
| Phase 2 | Module 1: Index Construction (离线, 100篇) | 未开始 |
| Phase 3 | Module 2: Question-to-Study (在线) | 未开始 |
| Phase 4 | Module 3: EBM Annotation and Analysis (在线) | 未开始 |
| Phase 5 | Pipeline Orchestrator & API | 未开始 |
| Phase 6 | Frontend (Streamlit) | 未开始 |
| Phase 7 | 集成测试 & 端到端验证 | 未开始 |

---

## Phase 0: 项目骨架 & 基础设施搭建

**目标：** 建立项目目录结构、依赖管理、配置系统、Docker 编排、数据库 schema。

### 任务清单

1. **创建项目目录结构**（按 architecture-design.md §8 的定义）
   ```
   ebm-online/
   ├── config/
   │   ├── settings.py          # Pydantic Settings
   │   └── .env.example
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
   ├── docker-compose.yml
   └── requirements.txt
   ```

2. **配置系统** (`config/settings.py`)
   - 使用 Pydantic Settings
   - 环境变量：`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ES_HOST`, `REDIS_URL`, `DATABASE_URL`
   - 模型配置：model name, temperature, pricing

3. **Docker Compose** (`docker-compose.yml`)
   - Elasticsearch 单节点 (port 9200)
   - Redis (port 6379)
   - Volume 持久化

4. **数据库初始化** (`src/storage/db.py`, `src/storage/models.py`)
   - SQLite 连接管理
   - 表结构：`pipeline_runs`, `llm_cache`, `llm_usage`
   - Migration 脚本

5. **requirements.txt**
   - fastapi, uvicorn, celery, redis
   - openai, pydantic, pydantic-settings
   - elasticsearch, httpx
   - numpy, scipy
   - streamlit
   - pytest

### 验证方式
- `docker-compose up` 能启动 ES + Redis
- `python -c "from config.settings import settings; print(settings)"` 正常输出
- SQLite 表创建成功

---

## Phase 1: Shared Infrastructure

**目标：** 实现 LLM Gateway（简化版，无限流/重试）和 Stats Engine。

### 1.1 LLM Gateway (`src/llm/gateway.py`)

**任务：**
1. 实现 `LLMGateway` 类，接口如 shared-infrastructure-design.md §2.2
2. 使用 OpenAI SDK，支持 structured output (response_format)
3. 内部流程：Cache check → API call → Parse → Cache save → Track usage

### 1.2 Cache Layer (`src/llm/cache.py`)

**任务：**
1. 实现 `CacheManager` 类
2. Cache key 生成：`hash(task_type + inputs + prompt_version)`
3. 只缓存 screening / extraction / rob 三种任务
4. SQLite 存储，表结构如 shared-infrastructure-design.md §3.5
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

---

## Phase 2: Module 1 — Index Construction (离线，小样本验证)

**目标：** 实现 PI Extraction、PI Normalization、Index Building。Step 1 和 Step 2 已完成（数据已在 `data/pmc-rct/`）。**初期只处理 100 篇文献做验证，确认流程跑通后再扩展到全量。**

### 2.1 PI Extraction (`src/modules/index/extraction.py`)

**任务：**
1. 读取 `data/pmc-rct/` 中的文献 JSON
2. 构建 prompt（从 title + abstract 提取 P 和 I 的 span）
3. 编写 prompt 模板 (`src/llm/prompts/pi_extraction.txt`)
4. 编写 JSON schema (`src/llm/schemas/pi_extraction.json`)
5. 初期 100 篇直接逐条调用，不必用 Batch API
6. 输出验证：P/I 非空、span 可定位
7. 结果持久化到 SQLite
8. 断点续跑支持

### 2.2 PI Normalization (`src/modules/index/normalization.py`)

**任务：**
1. Cleaning：HTML 去除、编码统一、多 span 合并
2. Concept Extraction：规则拆分复合描述
3. MeSH Mapping：调用 NLM MeSH Lookup API
4. Synonym Expansion：MeSH entry terms + 缩写映射表
5. Study-level Aggregation：生成 indexable_text

### 2.3 Index Building (`src/modules/index/indexing.py`)

**任务：**
1. ES index mapping 定义（`ebm_rct_index`）
2. Analyzer 配置（english_medical）
3. Bulk write（每批 1000 条）
4. 增量更新支持
5. 索引验证（文档总数、字段非空率、检索可用性）

### 验证方式
- PI Extraction：100 篇全部验证输出质量
- MeSH Mapping：已知术语能正确映射
- Index：执行 5 条已知 query，验证召回

---

## Phase 3: Module 2 — Question-to-Study (在线)

**目标：** 实现从临床问题到候选文献的完整流程。

### 3.1 Question Expansion (`src/modules/question/expansion.py`)

**任务：**
1. Prompt 模板 (`src/llm/prompts/question_expansion.txt`)
2. JSON schema (`src/llm/schemas/question_expansion.json`)
3. 输出：PICO + eligibility + preliminary analysis plan + confidence 标注
4. 错误处理：JSON 解析失败重试、非医学问题检测

### 3.2 Query Generation (`src/modules/question/query_gen.py`)

**任务：**
1. MeSH API 调用封装
2. 术语映射：P/I terms → MeSH preferred + entry terms
3. Boolean 组装：`(P_block) AND (I_block)`
4. Fallback：MeSH 未命中时使用原始术语

### 3.3 Index Search (`src/modules/question/search.py`)

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

### 4.1 Study Screening (`src/modules/analysis/screening.py`)

**任务：**
1. Prompt 模板 (`src/llm/prompts/screening.txt`)
2. JSON schema (`src/llm/schemas/screening.json`)
3. 逐篇调用，输出 include/exclude + rationale
4. 可缓存：cache key = study_id + pico_hash + prompt_version

### 4.2 Analysis Planning (`src/modules/analysis/planning.py`)

**任务：**
1. Prompt 模板 (`src/llm/prompts/analysis_planning.txt`)
2. 输入：preliminary plan + included studies summaries
3. 输出：confirmed_analysis_list（含 analysis_id 生成逻辑）
4. Validation：outcome_type 与 effect_measure 一致性

### 4.3 Data Extraction (`src/modules/analysis/extraction.py`)

**任务：**
1. Evidence Localization：从全文提取 abstract + results + tables
2. Prompt 模板 (`src/llm/prompts/extraction.txt`)
3. JSON schema (`src/llm/schemas/extraction.json`)
4. Per-study × per-analysis 调用
5. 数值合理性校验
6. 可缓存：cache key = study_id + analysis_id + evidence_hash + prompt_version

### 4.4 Risk of Bias (`src/modules/analysis/rob.py`)

**任务：**
1. Evidence Localization：从全文提取 abstract + methods
2. Prompt 模板 (`src/llm/prompts/rob.txt`)
3. JSON schema (`src/llm/schemas/rob.json`)
4. 5 域 LLM 评估 + Selective reporting 系统填充
5. overall_rob 规则计算
6. 可缓存：cache key = study_id + evidence_hash + prompt_version

### 4.5 Meta-analysis Aggregation (`src/modules/analysis/aggregation.py`)

**任务：**
1. Row Alignment：comparison/outcome/direction/unit 一致性检查
2. Statistical Derivation：调用 Stats Engine 的 derivation 模块
3. Single-study Effect 计算：调用 Stats Engine
4. Pooling：调用 Stats Engine（自动选择 method + model）
5. Heterogeneity 计算
6. 输出 AggregationResult

### 4.6 GRADE Assessment (`src/modules/analysis/grade.py`)

**任务：**
1. Prompt 模板 (`src/llm/prompts/grade.txt`)
2. JSON schema (`src/llm/schemas/grade.json`)
3. 五域判断：
   - Risk of bias：规则（high-RoB 占比）
   - Inconsistency：规则（I², Q p-value）
   - Indirectness：LLM（PICO 对齐）
   - Imprecision：LLM（CI + MID 判断）
   - Publication bias：固定 unable_to_determine
4. Overall certainty 计算（High → 逐级降）

### 验证方式
- Screening：用 mock 数据验证 include/exclude 逻辑
- Aggregation：用 Cochrane data-rows 验证数值正确性（pooled_effect 误差 < 0.01）
- 端到端：选 1 个问题完整跑通 Module 3

---

## Phase 5: Pipeline Orchestrator & API

**目标：** 实现 DAG 调度、状态管理、API 层。

### 5.1 Pipeline Orchestrator (`src/orchestrator/`)

**任务：**
1. `pipeline.py` — DAG 定义（模块间依赖关系）
2. `state.py` — 状态管理（pending → running → completed/failed/paused）
3. `tasks.py` — Celery task 定义
4. 断点续跑：从失败模块重新开始
5. WebSocket 进度推送

### 5.2 FastAPI Backend (`src/api/`)

**任务：**
1. `main.py` — FastAPI app 初始化
2. `routes/pipeline.py` — Pipeline CRUD API
3. `routes/results.py` — 结果查询 API
4. `routes/usage.py` — Token/Cost 查询 API
5. `websocket.py` — 实时进度推送

### 验证方式
- API：启动 uvicorn，通过 Swagger UI 测试各端点
- Orchestrator：提交一个问题，验证 pipeline 状态流转

---

## Phase 6: Frontend (Streamlit)

**目标：** 实现 4 页面的 Streamlit 前端。

### 任务清单

1. `frontend/app.py` — 主入口
2. `frontend/pages/1_question.py` — 问题输入页
3. `frontend/pages/2_pipeline.py` — Pipeline 总览页（状态流程图）
4. `frontend/pages/3_modules.py` — 模块详情页（screening 决策、extraction 数据）
5. `frontend/pages/4_results.py` — 结果展示页
   - Forest plot
   - GRADE Summary of Findings 表格
   - RoB traffic light plot
   - JSON 下载

### 验证方式
- `streamlit run frontend/app.py` 启动成功
- 提交问题 → 查看 pipeline 进度 → 查看结果

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
> "请执行 Phase 1.5 Stats Engine 的实现。参考 docs/shared-infrastructure-design.md §6 和 docs/implementation-plan.md。完成后用 Cochrane data-rows 做 regression test。"

---

## 进度记录

> 后续每完成一个 Phase，在此处更新状态和备注。

| 日期 | 完成内容 | 备注 |
|------|----------|------|
| 2026-05-08 | Phase 0: 项目骨架 & 基础设施搭建 | 全部完成并验证通过。PostgreSQL/Redis/ES 直接安装（非 Docker），8 个测试全部 PASSED。 |
