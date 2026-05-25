# Module 2 简化版测试指南

- **Status:** reference
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** Reference for Module 2 simplified testing workflow.


本文档用于验证 **Phase 3 简化版 Module 2（Question-to-Study）**：从 P/I 术语生成检索串；动态链路采用在线优先检索，并复用本地已清洗全文，缺失时再执行清洗与沉淀。

> 说明：当前实现默认不依赖 Elasticsearch；检索行为是本地加权 token overlap + 可选在线补全沉淀，主要用于小样本联调与回归。

## v2 沉淀索引（新增）

在线补全默认写入独立目录，不影响历史 demo 索引：

```text
data/retrieval_cache_v2/
├── index/local_rct_index_v2.jsonl
├── articles_raw/
├── articles_cleaned/
└── manifest/ingest_log.jsonl
```

动态链路行为（当前）：
1. 先在线 PubMed 检索（online-first）
2. 对返回候选检查本地 cleaned 是否已存在
3. 已存在 cleaned：直接复用
4. 缺失 cleaned：通过 `PMCID + PMC XML(JATS) 清洗` 生成 cleaned，并追加写入 `local_rct_index_v2.jsonl`
5. 无 PMCID / XML 清洗失败 / gate 失败：只写 `manifest` 失败事件，不进入可分析候选

清洗产物结构（`articles_cleaned/*.json`）：
- 顶层必填：`study_id`、`metadata`、`derived`、`xml_content`
- `xml_content.sections`: `[{ "section": "...", "text": "..." }]`
- `xml_content.tables`: `[{ "section_path": [...], "raw_xml": "<table-wrap ...>...</table-wrap>" }]`
- 严格校验：不兼容 `sections[].blocks`（legacy 结构会报错）

`LocalRCTIndex()` 默认路径已修复为：

- `data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl`

历史文件回填（把旧结构重洗为新结构）：

```bash
PYTHONPATH=backend/src .venv/bin/python -m ebm_backend.online_pipeline.interfaces.cli.reclean_retrieval_cache_v2 \
  --cache-root data/retrieval_cache_v2 \
  --index-path data/retrieval_cache_v2/index/local_rct_index_v2.jsonl
```

## 依赖与前置条件

1. **本地索引文件**（二选一）：
  - 若已存在：`data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl`
  - 若不存在：先按 [Phase 2 Demo Test Guide](phase2-demo-test-guide.md) 执行 `index-derived` 重建索引。
2. Python 环境与项目依赖已安装（与 Phase 0/2 相同）。
3. **使用真实 LLM（可选）**：根目录配置可用的 `.env`（`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_MODEL` 等，见 `config/settings.py`）。`Question Expansion`、`PI Extraction` 与 `MeSH / synonym expansion` 走 `LLMGateway` 结构化输出；优先使用 Responses API，若兼容端点没有 `/responses` 会自动降级到 Chat Completions。在线 Module 2 链路推荐使用 `LLMGateway(conn=None, ...)`，不依赖 SQLite。

## 与本地 100 篇索引匹配的示范问题（重要）

当前 `data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl` **只有 100 篇** `primary_rct` 子集，**语料里不一定包含**你关心的药物或疾病（例如全文检索 **没有** `metformin`）。若问题与索引无关，LLM 仍会生成很长的 Boolean query，但本地检索只能靠「糖尿病 / 血糖 / 成人」等泛词重叠，**Top hits 容易跑偏**——这是数据覆盖问题，不是单条 pipeline bug。

下面问题与索引中真实标题/摘要高度重合，用于 `Module2LLMRunner` 联调时 **Top1 更可预期**（已在本地 `LocalRCTIndex.search` 上核对）：


| 示范问题（中/英均可，建议英文化后检索更稳）                                                                                                                         | 典型 Top1 `study_id` |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| 留置导尿术后膀胱不适，度洛西汀是否有效？ / Duloxetine for catheter-related bladder discomfort after urinary catheterization                                        | `pmid:37877838`    |
| 咬合面龋坏、复合树脂修复后敏感，锌-碳酸盐羟基磷灰石是否有助于减轻术后敏感？ / Zinc-carbonate hydroxyapatite for postoperative sensitivity after composite in occlusal carious teeth | `pmid:36908720`    |
| 季节性过敏性鼻炎，无药鼻腔屏障喷雾（如膨润土）是否缓解花粉症状？ / Barrier-forming nasal spray for seasonal allergic rhinitis and grass pollen                                 | `pmid:36323243`    |
| 发作性睡病，solriamfetol 对真实道路驾驶表现的影响？ / Solriamfetol and on-the-road driving in narcolepsy                                                          | `pmid:36420633`    |


更完整的固定检索句见 [Phase 2 Demo Test Guide](phase2-demo-test-guide.md)「推荐测试 query」。

## 自动化测试（推荐）

在项目根目录执行：

```bash
pytest tests/unit/test_module2_question.py tests/unit/test_module2_llm.py -q
pytest tests/unit/test_retrieval_cache_v2.py -q
```

覆盖内容简述：


| 测试                                                                       | 说明                                                           |
| ------------------------------------------------------------------------ | ------------------------------------------------------------ |
| `test_query_generator_builds_boolean_query_and_dedupes`                  | P/I 离线 MeSH fallback、OR 块、`AND` 组合、去重                        |
| `test_question_expander_from_pico`                                       | 给定 PICO 时的扩写结果结构                                             |
| `test_question_to_study_local_search_returns_candidates`                 | 端到端：查询 → 本地索引 → 非空候选列表（无索引时会从 `derived` 临时构建）                |
| `test_clinical_question_retrieval_ranks_duloxetine_catheter_trial_first` | 固定临床问题 + 对齐语料的 P/I → Top1 为 `pmid:37877838`（度洛西汀 + 导尿相关膀胱不适） |
| `test_expand_with_llm_maps_payload`                                      | Mock LLM：Question Expansion JSON → `QuestionExpansionResult` |
| `test_generate_with_llm_merges_extra_terms`                              | Mock LLM：额外检索词合并后再走 Boolean 组装                               |
| `test_question_pi_extractor_with_llm_uses_no_sql_gateway`                | Mock LLM：PI 提取使用 `LLMGateway(conn=None)`，不访问 SQL             |
| `test_module2_llm_runner_returns_downstream_payload`                     | Mock LLM：端到端返回 `Module2LLMResult`，可直接传给下游                    |
| `test_v2_not_used_when_local_hits_sufficient`                            | 本地命中已足够时，不触发在线请求 |
| `test_v2_backfill_ingests_and_reuses`                                    | 本地不足时触发在线补全，清洗成功后写入 v2 索引并可被同次检索复用 |
| `test_v2_logs_no_pmcid_and_does_not_index`                               | 无 PMCID 场景记录失败状态，不入可分析索引 |


可选：与 Module 1 一起回归：

```bash
pytest tests/unit/test_module2_question.py tests/unit/test_module2_llm.py tests/unit/test_module1_pipeline.py -q
```

## 手动联调（Python 交互）

确保索引已存在后，在项目根目录打开 Python：

```python
from pathlib import Path
from ebm_backend.online_pipeline.application.question_study import PICO, QueryGenerator, QuestionExpander, QuestionStudySearcher

index_path = Path("data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl")
assert index_path.exists(), "请先运行: python -m ebm_backend.index_construction.interfaces.cli index-derived --data-root data/data_for_test/data_demo_with_mesh"

question = "龋齿患者使用羟基磷灰石的相关 RCT？"
pico = PICO(
    population=["dental caries"],
    intervention=["hydroxyapatite"],
)
expansion = QuestionExpander().from_pico(question, pico)
query_out = QueryGenerator().generate(
    population=expansion.pico.population,
    intervention=expansion.pico.intervention,
)
print("boolean_query:", query_out.boolean_query)

searcher = QuestionStudySearcher(index_path=index_path)
result = searcher.search_from_query_output(query_out, top_k=5)
print("returned:", result.returned_count)
for s in result.studies:
    print(s.study_id, s.title[:80], "score=", s.relevance_score)
```

预期：`returned_count > 0`，且 `boolean_query` 中含引号包裹的短语与 `OR` / `AND`。

### 使用 LLM 的端到端 Module 2（真实环境，无 SQL）

建议用 heredoc 一次性执行，不要逐行粘贴进 Python REPL；逐行粘贴容易因为 `async def main()` 缩进块提前结束而报 `IndentationError`。

```bash
python - <<'PY'
import asyncio
from pathlib import Path

from openai import AsyncOpenAI

from ebm_backend.shared.config.settings import settings
from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.question_study import Module2LLMRunner

gateway = LLMGateway(
    conn=None,
    client=AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url),
)

async def main():
    q = "In adults undergoing surgery with a urinary catheter, does duloxetine reduce catheter-related bladder discomfort compared with placebo？"
    runner = Module2LLMRunner(gateway, index_path=Path("data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl"))
    result = await runner.run(q, top_k=5)

    print("expanded_question:", result.expansion.expanded_question)
    print("PI population:", result.pi.population)
    print("PI intervention:", result.pi.intervention)
    print("boolean_query:", result.query.boolean_query)
    print("hits:", result.search.returned_count)
    for study in result.search.studies:
        print(study.study_id, study.title[:80], "score=", study.relevance_score)

asyncio.run(main())
PY
```

## 与 CLI 检索的对照

同一套底层索引也可直接用 Module 1 CLI 查原文本（便于对照 score 与命中）：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --index-path data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl \
  --query "dental caries hydroxyapatite" \
  --top-k 5
```

Module 2 会把 Boolean 串中的引号内短语抽出后交给 `LocalRCTIndex.search`，因此与上述自由文本 query 在 token 层面应大致可比，但**不必**逐字段完全一致。

## 已知限制（简化版）

- **Question Expansion**：无 LLM 时仍可用 `expand()` 确定性骨架；接 LLM 时使用 `backend/src/ebm_backend/shared/llm/prompts/question_expansion.txt` 与 `backend/src/ebm_backend/shared/llm/schemas/question_expansion.json`。
- **PI Extraction**：`QuestionPIExtractor.extract_with_llm()` 使用 `backend/src/ebm_backend/shared/llm/prompts/question_pi_extraction.txt` 与 `backend/src/ebm_backend/shared/llm/schemas/question_pi_extraction.json`，从扩写结果中提取检索用 P/I。
- **MeSH / synonym expansion**：`QueryGenerator.generate_with_llm()` 使用 `backend/src/ebm_backend/shared/llm/prompts/query_generation.txt` 与 `backend/src/ebm_backend/shared/llm/schemas/query_generation.json`，由 LLM 给出 MeSH-like preferred terms、entry terms 和额外检索词，再组装 Boolean query。
- **检索**：静态模式为本地加权 token overlap（非 ES）；动态模式为在线优先 + 本地 cleaned 复用 + 缺失时清洗沉淀。

## 相关代码路径

- `backend/src/ebm_backend/online_pipeline/application/question_study/expansion.py` — `QuestionExpander.expand` / `expand_with_llm` / `expand_with_llm_sync`
- `backend/src/ebm_backend/online_pipeline/application/question_study/pi.py` — `QuestionPIExtractor.extract_with_llm`
- `backend/src/ebm_backend/online_pipeline/application/question_study/query_gen.py` — `QueryGenerator.generate` / `generate_with_llm` / `generate_with_llm_sync`
- `backend/src/ebm_backend/online_pipeline/application/question_study/runner.py` — `Module2LLMRunner`，返回可给下游使用的 `Module2LLMResult`
- `backend/src/ebm_backend/online_pipeline/application/question_study/llm_io.py` — 加载 `shared/llm/prompts/*.txt` 与 `shared/llm/schemas/*.json`
- `backend/src/ebm_backend/online_pipeline/application/question_study/search.py` — `QuestionStudySearcher`、`CandidateStudy`
- `backend/src/ebm_backend/online_pipeline/application/question_study/retrieval_cache_v2.py` — v2 在线优先检索 + cleaned 复用 + 缺失清洗沉淀逻辑
- `tests/unit/test_module2_question.py` — 离线路径单测
- `tests/unit/test_module2_llm.py` — LLM 路径单测（Mock Responses）
