# EBM Online Pipeline

自动化循证医学（Evidence-Based Medicine）pipeline。当前仓库已经能跑通一条简化闭环：

- FastAPI 后端：提交 clinical question，返回 run 状态、trace、results
- Gradio 单页前端：输入问题，查看 Module 2/3 中间过程和结果
- 本地 1000 篇 demo 索引：用于检索和端到端演示

当前主路径是 Phase 5 + Phase 6。它不依赖 PostgreSQL、Redis、Celery 或 Docker Compose。

## 当前状态

当前仓库里真正可用、且已经接线的部分：

- Phase 2 简化版：本地 JSONL 索引与检索
- Phase 3 简化版：Question Expansion / PI Extraction / Query Generation / Local Search
- Phase 4 简化版：Screening / Planning / Extraction / Risk of Bias / Aggregation / GRADE
- Phase 5 简化版：进程内后台执行、FastAPI `/pipeline/runs`、`/trace`、`/results`
- Phase 6 简化版：Gradio 单页 demo `frontend/gradio_app.py`

当前不属于主启动路径、但代码里还保留的能力：

- Module 1 的部分流程仍保留数据库存储接口
- 一些单元测试仍覆盖 SQLite/PostgreSQL 适配
- Elasticsearch 仍用于 Phase 2 / 本地索引相关能力

所以 README 需要区分两件事：

- “现在怎么跑起来”：不需要数据库
- “仓库里是否还存在数据库相关代码”：存在，但不是当前主路径的启动前置

## 环境要求

- Python 3.10+
- Git
- 可选：OpenAI-compatible API key（真实 LLM 模式需要）
- 可选：Elasticsearch 8.x（只在你要跑 Phase 2 / ES 相关能力时需要）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Jerry-LHT/EBM-Online.git
cd EBM-Online
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

如果创建 venv 报错 `ensurepip is not available`：

```bash
apt install -y python3.10-venv
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

默认可以先不填 `OPENAI_API_KEY`，这样你仍然可以跑 mock 路径。

真实 LLM 模式至少需要：

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-5.2
```

### 5. 验证配置加载

```bash
PYTHONPATH=backend/src python -c "from ebm_backend.shared.config.settings import settings; print(settings.llm_model, bool(settings.openai_api_key))"
```

## 启动方式

### 方式 A：只跑前端 mock 演示

这是最轻的启动方式，不需要 API key，也不需要单独起 FastAPI。

```bash
PYTHONPATH=backend/src python frontend/gradio_app.py --host 127.0.0.1 --port 7860
```

打开：

```text
http://127.0.0.1:7860
```

然后在页面里勾选 `Use mock LLM`。

### 方式 B：跑真实的 FastAPI + Gradio 链路

先启动 API：

```bash
PYTHONPATH=backend/src python -m uvicorn ebm_backend.online_pipeline.interfaces.api.main:app --host 127.0.0.1 --port 8000
```

我已实际验证过这条命令可以启动，且：

```bash
curl -s http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok"}
```

再开另一个终端启动 Gradio：

```bash
PYTHONPATH=backend/src python frontend/gradio_app.py --host 127.0.0.1 --port 7860
```

默认 `BACKEND_BASE_URL` 是 `http://127.0.0.1:8000`。如果你改了 API 端口，启动 Gradio 前先设置：

```bash
export BACKEND_BASE_URL=http://127.0.0.1:8000
```

### 方式 C：直接调用 API

启动 API 后，可直接提交一个 run：

```bash
curl -s -X POST http://127.0.0.1:8000/pipeline/runs \
  -H "Content-Type: application/json" \
  -d '{"question":"In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?","top_k":5,"use_mock":true}'
```

说明：

- `use_mock=true`：不需要真实 API key，适合结构 smoke
- `use_mock=false`：需要 `.env` 中有可用的真实 LLM 配置

## 数据库说明

当前主路径不需要 PostgreSQL。

README 之前写 `PostgreSQL 14+` 是不准确的，原因是把“仓库里仍保留的数据库代码”误写成了“当前启动必需项”。实际情况是：

- Phase 5 API 当前使用进程内 `InMemoryPipelineStore`
- Phase 6 Gradio 当前通过 API 轮询 trace，不依赖数据库
- `run_pipeline.py` 的真实/模拟主路径也不要求数据库启动

数据库相关代码仍然存在，主要用于：

- Module 1 的部分存储流程
- LLM cache / tracker / persistence 适配层
- 某些 SQLite/PostgreSQL 测试

所以现在正确表述应当是：

- 跑当前前后端 demo：不需要数据库
- 做 Module 1 存储链路或相关测试：可能需要数据库或 SQLite 路径

## 测试

推荐先跑当前主路径相关测试：

```bash
PYTHONPATH=backend/src pytest tests/unit/test_phase5_api.py tests/unit/test_phase6_gradio_app.py -q
```

我已实际验证过，上面这组测试当前通过。

常用回归：

```bash
PYTHONPATH=backend/src pytest \
  tests/unit/test_module2_question.py \
  tests/unit/test_module2_llm.py \
  tests/unit/test_module3_analysis.py \
  tests/unit/test_phase5_orchestrator.py \
  tests/unit/test_phase5_api.py \
  tests/unit/test_phase6_gradio_app.py \
  -q
```

如果你要看前端 mock 回调是否可单独跑通：

```bash
PYTHONPATH=backend/src python - <<'PY'
from frontend.gradio_app import DEFAULT_INDEX_PATH, DEFAULT_QUESTION, run_pipeline

outputs = run_pipeline(DEFAULT_QUESTION, DEFAULT_QUESTION, 1, True, DEFAULT_INDEX_PATH)
staged = list(outputs)
print(staged[-1][0])
print(staged[-1][14]["status"])
print(staged[-1][15])
PY
```

## 项目结构

```text
backend/src/ebm_backend/
  index_construction/   Module 1
  online_pipeline/      Module 2/3 + Orchestrator + FastAPI
  shared/               config / llm / persistence / statistics
frontend/
  gradio_app.py         当前前端入口
experiments/
  code/                 实验脚本与 notebook
  data/                 实验输入数据
  results/              实验输出与结果
data/
  测试与示例数据
tests/
  单元测试与集成测试
docs/
  设计与测试文档
```

## 文档

- [docs/README.md](docs/README.md)
- [架构设计](docs/architecture/architecture-design.md)
- [Module 1 详细设计](docs/design/module1-detail-design.md)
- [Module 2 详细设计](docs/design/module2-detail-design.md)
- [Module 2 测试指南](docs/guides/module2-test-guide.md)
- [Module 3 详细设计](docs/design/module3-detail-design.md)
- [Module 3 测试指南](docs/guides/module3-test-guide.md)
- [Phase 5 API 测试指南](docs/guides/phase5-api-test-guide.md)
- [Phase 6 Gradio Demo 测试与调试指南](docs/guides/phase6-gradio-demo-guide.md)
