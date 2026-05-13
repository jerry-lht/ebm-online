# Phase 6 Gradio Demo 测试与调试指南

本文档用于验证 **Phase 6 Gradio Demo**：用户像使用模型对话界面一样输入 clinical question，页面通过 FastAPI 创建 pipeline run 并轮询 trace，在同一页展示 Phase 5 trace、Module 2 中间过程、Module 3 分析结果和完整 JSON trace。

> 说明：当前 Phase 6 是轻量 demo。真实模式依赖 FastAPI 服务；`use_mock=true` 时不依赖外部 uvicorn，而是走本地 `TestClient` 做 smoke、UI 调试和自动化测试。

## 当前实现范围

已完成的 demo 能力：

1. `frontend/gradio_app.py`：Gradio Blocks 单页入口。
2. 左侧输入 clinical question、推荐 demo 问题、`top_k`、`use_mock`、本地索引路径。
3. 右侧 ChatGPT-like 主回答和 run summary。
4. Pipeline timeline：`question_expansion -> question_pi_extraction -> query_generation -> local_search -> module3_analysis`。
5. 分 Tab 展示 PICO、eligibility、analysis plan、PI extraction、Boolean query、本地检索 query_text、候选文献、screening、extraction、Risk of Bias、aggregation/GRADE。
6. 完整 trace JSON 页面展示，并生成可下载的 `/tmp/ebm_pipeline_trace_<run_id>.json`。
7. failed run 会显示错误信息，同时保留已完成步骤 trace，便于调试。

## 相关代码路径

- `frontend/gradio_app.py` — Gradio demo 入口和 UI callback
- `backend/src/ebm_backend/online_pipeline/interfaces/api/routes_pipeline.py` — Phase 5 run 创建与 trace API
- `backend/src/ebm_backend/online_pipeline/infrastructure/pipeline_repository.py` — run / step trace 状态结构
- `tests/unit/test_phase6_gradio_app.py` — Gradio callback 和 Blocks 构建 smoke test
- `docs/guides/phase5-api-test-guide.md` — 后端 API 与 orchestrator 调试指南

## 安装依赖

```bash
pip install -r requirements.txt
```

确认 Gradio 可导入：

```bash
python - <<'PY'
import gradio as gr
print(gr.__version__)
PY
```

## 启动 Demo

启动 Gradio demo：

```bash
PYTHONPATH=backend/src uvicorn ebm_backend.online_pipeline.interfaces.api.main:app --host 127.0.0.1 --port 8000 --log-level debug
PYTHONPATH=backend/src python frontend/gradio_app.py --host 127.0.0.1 --port 7860
```

打开：

```text
http://127.0.0.1:7860
```

如果 7860 被占用，换一个端口：

```bash
python frontend/gradio_app.py --host 127.0.0.1 --port 7861
```

允许局域网访问：

```bash
python frontend/gradio_app.py --host 0.0.0.0 --port 7860
```

## 页面使用方式

1. 选择一个 demo question，或直接在输入框写 clinical question。
2. 默认 `Use mock LLM` 不勾选，会跑真实 LLM；建议先把 `Top K` 调到 `1` 控制调用量。
3. 点击 `Run pipeline`。
4. 先看右侧主回答区：状态、耗时、纳入/排除数量、主要结果。
5. 展开 `Pipeline timeline` 检查每一步摘要。
6. 依次查看各 Tab：
   - `Question`：PICO、eligibility、preliminary/module3 analysis plan、PI extraction。
   - `Search`：Boolean query、本地检索 query_text、Top candidate studies。
   - `Screening`：纳入/排除判断和理由。
   - `Extraction`：每个 study × analysis 的抽取数据行。
   - `Risk of Bias`：各 RoB domain judgement。
   - `Aggregation / GRADE`：汇总效应、异质性、GRADE Summary of Findings。
   - `Trace JSON`：完整 run state 和可下载 JSON。

## Mock / Real 模式

### Real LLM 模式

默认不勾选 `Use mock LLM`。运行前确认项目 `.env` 包含：

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
LLM_MODEL=...
```

真实模式会产生外部 LLM 调用和费用。建议先把 `Top K` 调到 `1`，并使用 demo question：

```text
In patients undergoing surgery, do nerve blocks reduce postoperative pain compared with usual analgesia?
```

### Mock 模式

勾选 `Use mock LLM`：

- 不需要真实 API key。
- 使用 `SimplifiedPipelineMockGateway` 返回确定性结构化结果。
- 适合检查 trace 字段、调试本地检索和表格展示，不消耗 LLM 调用。

## 自动化测试

只跑 Phase 6 Gradio demo：

```bash
PYTHONPATH=backend/src pytest tests/unit/test_phase6_gradio_app.py -q
```

覆盖内容：

| 测试 | 说明 |
|------|------|
| `test_phase6_gradio_mock_callback_returns_trace_and_tables` | 用临时 JSONL 索引直接调用 `run_pipeline(..., use_mock=True)`，确认主回答、HTML 表格、完整 trace 和 trace 文件都生成 |
| `test_phase6_gradio_empty_question_does_not_run_pipeline` | 空问题不会触发 pipeline，返回 `not_started` |
| `test_phase6_gradio_blocks_app_builds` | `build_app()` 可成功构建 Gradio Blocks |
| `test_phase6_gradio_defaults_to_real_llm_mode` | 确认页面默认不勾选 `Use mock LLM`，即默认真实 LLM 模式 |

Phase 5 + Phase 6 联合回归：

```bash
PYTHONPATH=backend/src pytest \
  tests/unit/test_phase5_orchestrator.py \
  tests/unit/test_phase5_api.py \
  tests/unit/test_phase6_gradio_app.py \
  -q
```

更完整的 Module 2/3/5/6 回归：

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

## 调试方法

### 1. 先确认不是依赖问题

```bash
PYTHONPATH=backend/src python -m py_compile frontend/gradio_app.py
PYTHONPATH=backend/src python - <<'PY'
from frontend.gradio_app import build_app
app = build_app()
print(type(app).__name__, len(app.blocks))
PY
```

### 2. 不开浏览器，直接跑 callback

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

`outputs[14]` 是完整 trace dict，`outputs[15]` 是下载用 JSON 文件路径。

### 3. 查看 trace 文件

```bash
ls -lh /tmp/ebm_pipeline_trace_*.json
python -m json.tool /tmp/ebm_pipeline_trace_<run_id>.json | less
```

重点检查：

- `steps[*].status`
- `steps[*].summary`
- `steps[*].payload`
- `result.query.boolean_query`
- `result.search.query_text`
- `result.candidates`
- `result.screening`
- `result.extraction.rows`
- `result.risk_of_bias.assessments`
- `result.aggregation.analyses`
- `result.grade.assessments`

### 4. 本地检索无命中

先确认索引存在：

```bash
test -f data/data_for_test/data_demo_1000/index/local_rct_index.jsonl
```

若不存在，从 demo derived 重建：

```bash
python -m ebm_backend.index_construction.interfaces.cli index-derived \
  --data-root data/data_for_test/data_demo_1000
```

如果真实模式随机问题无命中，优先换成 demo question；1000 篇样本不是全医学语料，检索覆盖有限。

### 5. 端口占用

```bash
python - <<'PY'
import socket
s = socket.socket()
print(s.connect_ex(("127.0.0.1", 7860)))
s.close()
PY
```

返回 `0` 表示端口已被占用。换端口启动：

```bash
python frontend/gradio_app.py --port 7861
```

### 6. 常见问题

| 问题 | 处理 |
|------|------|
| `ModuleNotFoundError: gradio` | 运行 `pip install -r requirements.txt` |
| 页面能打开但 run 失败 | 打开 `Trace JSON` 看 failed step 的 `error`；mock 模式通常用于先排除 UI 和索引问题 |
| Real 模式提示缺少 API key | 设置 `.env` 或环境变量；临时调 UI 时可勾选 `Use mock LLM` |
| Real 模式很慢 | 把 `Top K` 调到 `1`；先用 mock 模式确认 UI |
| 候选文献为空 | 检查索引路径，或换用 demo-aware 推荐问题 |

## 当前限制

- 真实模式通过轮询 `/pipeline/runs/{run_id}/trace` 逐步刷新，但不是 WebSocket 推送。
- 不保存历史记录；刷新页面后只能看当前浏览器状态和下载的 trace JSON。
- 不做登录、多用户隔离、数据库持久化或复杂图表。
- 表格当前用 HTML 渲染，避免 Gradio Dataframe 在部分 NumPy/pyarrow 环境中触发 ABI 问题。
