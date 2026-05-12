# EBM Online Pipeline

自动化循证医学 (Evidence-Based Medicine) Pipeline，从临床问题出发，自动完成文献检索、筛选、数据抽取、Meta 分析和 GRADE 评估。

## 快速开始

### 环境要求

- Python 3.10+
- Git
- PostgreSQL 14+
- Redis 7+（后续 Celery/后台任务扩展需要；Phase 5 简化版不需要）
- Elasticsearch 8.x（Phase 2 需要）

### 1. 克隆仓库

```bash
git clone https://github.com/Jerry-LHT/EBM-Online.git
cd EBM-Online
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate

# 如果创建 venv 报错 "ensurepip is not available"：
apt install -y python3.10-venv   # 然后重新创建
# 或者用 --without-pip 创建后手动引导 pip：
python3 -m venv --without-pip .venv
source .venv/bin/activate
python3 -m pip install --target=.venv/lib/python3.10/site-packages pip
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 编辑根目录 .env，将 sk-your-key-here 替换为你的真实 OPENAI_API_KEY
# 注意：不创建 .env 会导致 settings 加载报错（openai_api_key 为必填字段）
```

### 5. 启动基础设施

#### 方式 A：直接安装（推荐，适用于当前环境）

```bash
# PostgreSQL（如果还没装）
apt install -y postgresql postgresql-client
service postgresql start

# 创建用户和数据库
su - postgres -c "psql -c \"CREATE USER ebm WITH PASSWORD 'ebm123';\""
su - postgres -c "psql -c \"CREATE DATABASE ebm_online OWNER ebm;\""

# 验证
pg_isready
PGPASSWORD=ebm123 psql -h localhost -U ebm -d ebm_online -c "SELECT 1"
```

Redis 和 Elasticsearch 在后续扩展需要时再安装：

```bash
# Redis（后续 Celery/后台任务扩展需要）
apt install -y redis-server
service redis-server start

# Elasticsearch（Phase 2 需要）
# 参考官方文档安装: https://www.elastic.co/guide/en/elasticsearch/reference/8.17/deb.html
```

#### 方式 B：Docker Compose（需要完整 Docker 权限）

```bash
docker compose up -d
```

这会一键启动 PostgreSQL + Elasticsearch + Redis。

> 注意：如果你的环境是容器或受限虚拟机，Docker daemon 可能无法启动（缺少 iptables 权限），请用方式 A。

### 6. 初始化数据库

```bash
python3 -c "from ebm_backend.shared.persistence.db import init_db; from ebm_backend.shared.config.settings import settings; init_db(settings.database_url)"
```

### 7. 验证安装

```bash
# 配置加载（需要先创建 .env）
python3 -c "from ebm_backend.shared.config.settings import settings; print(settings.model_dump_json(indent=2))"

# 运行测试
python3 -m pytest tests/ -v
```

期望结果：配置正常输出 JSON，单元测试通过。当前仓库包含 Module 1/2/3 的简化版单元测试，建议按 `docs/*-test-guide.md` 分模块验收。

### 当前实现状态

- **已完成：** Phase 0、Phase 1
- **Phase 2 已完成简化版：** `data_demo_with_mesh/` 100 篇样本、本地 JSONL 索引、固定 query 检索验证、CLI 检索入口
- **Phase 3 已完成简化版：** Question Expansion / PI Extraction / Query Generation / Local Search 的 no-SQL LLM 链路和 mock 单测
- **Phase 4 已完成简化版：** Module 3 screening、planning、extraction、RoB、StatsEngine aggregation、GRADE 的 mock LLM 闭环和 CLI smoke
- **Phase 5 已完成简化版：** 同步 Pipeline Orchestrator、进程内 run state、FastAPI `/pipeline/runs`、`/trace`、`/results`，可查看 Module 2/3 中间过程
- **Phase 6 已完成轻量 demo：** Gradio 单页前端 `frontend/gradio_app.py`，可像模型对话一样提问，并展示 timeline、PICO、检索、screening、extraction、RoB、aggregation/GRADE 和完整 trace JSON
- **后续扩展：** 真实 OpenAI Batch、真实 Elasticsearch bulk、数据库 run 状态、Celery/Redis 后台任务、WebSocket、缓存、usage tracking、历史记录、多用户前端

## 项目结构

```
ebm-online/
├── config/              # 配置系统 (Pydantic Settings)
├── src/
│   ├── orchestrator/    # Pipeline 调度
│   ├── modules/
│   │   ├── index/       # Module 1: 文献索引构建
│   │   ├── question/    # Module 2: 问题到文献
│   │   └── analysis/    # Module 3: EBM 标注与分析
│   ├── llm/             # LLM Gateway, Cache, Tracker
│   ├── stats/           # 统计引擎 (Meta-analysis)
│   ├── storage/         # PostgreSQL + Elasticsearch
│   └── api/             # FastAPI 后端
├── frontend/            # Gradio demo + Streamlit 占位
├── data/pmc-rct/        # PMC RCT 文献数据 (67,501篇)
├── tests/               # 测试
├── docs/                # 设计文档
├── docker-compose.yml   # 基础设施编排（可选）
└── requirements.txt     # Python 依赖
```

## 技术栈

| 组件 | 技术选型 |
|------|----------|
| 后端 API | FastAPI |
| 任务调度 | Celery + Redis |
| LLM | OpenAI SDK (gpt-5.2) |
| 搜索引擎 | Elasticsearch |
| 数据库 | PostgreSQL（测试环境可使用 SQLite 适配） |
| 统计计算 | NumPy + SciPy |
| 前端 | Gradio demo（当前）/ Streamlit（占位） |

## 开发

### 运行测试

```bash
# 全部测试
python3 -m pytest tests/ -v

# 仅单元测试
python3 -m pytest tests/unit/ -v

# 带覆盖率
python3 -m pytest tests/ --cov=src --cov-report=html
```

分模块快速验收：

```bash
# Module 2 + StatsEngine + Module 3 简化闭环
pytest tests/unit/test_module2_question.py tests/unit/test_stats_engine.py tests/unit/test_module3_analysis.py -q

# Phase 5 Orchestrator/API 简化闭环
pytest tests/unit/test_phase5_orchestrator.py tests/unit/test_phase5_api.py -q

# Phase 6 Gradio demo smoke
pytest tests/unit/test_phase6_gradio_app.py -q

# Module 2 + Module 3 + Phase 5 + Phase 6 联合回归
pytest tests/unit/test_module2_question.py tests/unit/test_module2_llm.py tests/unit/test_module3_analysis.py tests/unit/test_phase5_orchestrator.py tests/unit/test_phase5_api.py tests/unit/test_phase6_gradio_app.py -q

# Module 3 mock CLI smoke
python -m ebm_backend.online_pipeline.interfaces.cli.evidence_analysis \
  --mock \
  --question "Does duloxetine reduce catheter-related bladder discomfort?" \
  --population "catheter-related bladder discomfort" \
  --intervention "duloxetine" \
  --comparison "placebo" \
  --outcome "catheter-related bladder discomfort incidence" \
  --top-k 3
```

启动 Phase 5 API：

```bash
uvicorn ebm_backend.online_pipeline.interfaces.api.main:app --reload --host 0.0.0.0 --port 8000
```

提交 1000 篇索引真实 pipeline run：

```bash
curl -s -X POST http://127.0.0.1:8000/pipeline/runs \
  -H "Content-Type: application/json" \
  -d '{"question":"In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?","top_k":5,"use_mock":false}'
```

无 API key 时可把 `use_mock` 改为 `true` 做结构 smoke。常用回归：

```bash
pytest tests/unit/test_module2_question.py \
  tests/unit/test_module2_llm.py \
  tests/unit/test_module3_analysis.py \
  tests/unit/test_phase5_orchestrator.py \
  tests/unit/test_phase5_api.py -q
```

启动 Phase 6 Gradio demo：

```bash
python frontend/gradio_app.py --host 127.0.0.1 --port 7860
```

打开：

```text
http://127.0.0.1:7860
```

页面默认不勾选 `Use mock LLM`，会走真实 LLM；需要无 API key 结构 smoke 时再勾选 mock。调试时优先直接跑 mock callback，避免消耗真实 LLM：

```bash
python - <<'PY'
from frontend.gradio_app import DEFAULT_INDEX_PATH, DEFAULT_QUESTION, run_pipeline
outputs = run_pipeline(DEFAULT_QUESTION, DEFAULT_QUESTION, 1, True, DEFAULT_INDEX_PATH)
print(outputs[0])
print(outputs[14]["status"])
print(outputs[15])
PY
```

### 停止服务

```bash
# 直接安装方式
service postgresql stop
service redis-server stop

# Docker 方式
docker compose down        # 停止容器（保留数据）
docker compose down -v     # 停止容器并删除数据
```

## 文档

详细设计文档在 `docs/` 目录：

- [架构设计](docs/architecture-design.md)
- [共享基础设施设计](docs/shared-infrastructure-design.md)
- [数据 Pipeline 规格](docs/data-pipeline-for-online-ebm.md)
- [Module 1 详细设计](docs/module1-detail-design.md)
- [Phase 2 Demo 测试文档](docs/phase2-demo-test-guide.md)
- [Module 2 详细设计](docs/module2-detail-design.md)
- [Module 2 测试指南](docs/module2-test-guide.md)
- [Module 3 详细设计](docs/module3-detail-design.md)
- [Module 3 测试指南](docs/module3-test-guide.md)
- [Phase 5 API 测试指南](docs/phase5-api-test-guide.md)
- [Phase 6 Gradio Demo 测试与调试指南](docs/phase6-gradio-demo-guide.md)
- [实现计划](docs/implementation-plan.md)
