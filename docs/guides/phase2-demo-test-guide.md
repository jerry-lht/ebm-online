# Phase 2 Demo Test Guide

- **Status:** reference
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** Reference for Module 1 simplified demo/index workflow.


本文档用于验证“简化版 Module 1”路径：demo 数据集 -> PI 抽取 -> PI 映射 -> 本地轻量索引 -> 检索测试。

当前 demo 数据统一放在 `data/data_for_test/`：

- `data/data_for_test/data_demo/`：早期 100 篇基础 demo。
- `data/data_for_test/data_demo_with_mesh/`：早期 100 篇 PI-first derived + 本地索引 demo。
- `data/data_for_test/data_demo_1000/`：主题簇优先选取的 1000 篇 demo，用于 Module 2/3 后续调试。

## 当前完成状态

简化版 Module 1 的核心功能已经完成，可以用于 Phase 2 小样本验证：

- 已有 `data/data_for_test/data_demo_with_mesh/derived/*.json` 可作为 100 篇 PI-first 派生结果。
- 已完成 `data/data_for_test/data_demo_1000/` 的 1000 篇主题簇数据集、PI 抽取、映射、本地索引构建和检索 smoke test。
- 已可从 derived JSON 直接构建本地 JSONL 检索索引。
- 已可输入临床/医学 query，返回候选 study、score、matched fields、title、P/I、MeSH 和原文路径。
- 当前 100 个 derived 文件均可入索引，固定 5 条 query 验证为 5/5 通过。

尚未视为生产版完成的内容：

- LLM PI 抽取质量还需要继续优化；部分文章会出现空 PI 或非 literal span。
- 真实 OpenAI-compatible Batch API、失败自动重提和成本统计尚未作为主路径验收。
- 真实 Elasticsearch bulk 写入和在线服务化检索尚未纳入当前简化版。
- 当前本地检索是轻量 token overlap + 字段权重，适合 Phase 2 验证，不等价于最终 ES 检索排序。

## 目标

- 使用 `data/data_for_test/data_demo_with_mesh/derived/*.json` 或 `data/data_for_test/data_demo_1000/derived/*.json` 作为 PI-first 派生输入
- 从 derived JSON 重建对应的 `index/local_rct_index.jsonl`
- 执行固定 query 检索验证
- 输入自定义 query，查看检索后的候选 study、score、matched fields、P/I 和 MeSH 输出
- 如需重跑 PI，可选择本地 PI 模式或真实 LLM PI 模式

## 前置条件

当前推荐验收路径只依赖本地文件：

- `data/data_for_test/data_demo_with_mesh/derived/` 或 `data/data_for_test/data_demo_1000/derived/` 已存在 PI-first JSON
- Python 依赖已安装

只有在重新跑真实 LLM PI 抽取或数据库状态回写时，才需要：

- 根目录 `.env` 已配置并可用
- PostgreSQL 可连接
- OpenAI-compatible Chat Completions API 可连接
- `data/data_for_test/data_demo/` 已生成

## 运行方式

### 1. 从已有 derived 重建本地索引

这是当前推荐的最快验收路径。它不会调用 LLM，不依赖数据库，只读取 derived JSON。

```bash
python -m ebm_backend.index_construction.interfaces.cli index-derived \
  --data-root data/data_for_test/data_demo_with_mesh
```

预期输出摘要：

```json
{
  "data_root": "data/data_for_test/data_demo_with_mesh",
  "export_dir": "data/data_for_test/data_demo_with_mesh/derived",
  "index_path": "data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl",
  "studies_total": 100,
  "indexed": 100,
  "failed": 0,
  "queries_passed": 5,
  "queries_total": 5
}
```

### 2. 输入 query 查看检索结果

使用 `search-local` 查看检索后的输出：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --index-path data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl \
  --query "duloxetine catheter-related bladder discomfort" \
  --top-k 3
```

输出字段说明：

- `study_id`：内部 study id，优先使用 PMID。
- `score`：本地检索分数，越高越靠前。
- `matched_fields`：命中的索引字段，例如 `title`、`population`、`intervention`、`mesh_terms`。
- `title`：文章标题。
- `population` / `intervention`：PI 抽取和归一化后的检索字段。
- `mesh_terms`：文章级 PMID 回填 MeSH。
- `mesh_population` / `mesh_intervention`：PI concept 映射到的 MeSH。
- `article_path`：原始 demo 文章 JSON 路径。

### 3. 1000 篇 demo：选样、PI 抽取和索引

先从 `data/pmc-rct` 中选取 1000 篇主题簇优先的 `primary_rct`：

```bash
python -m ebm_backend.index_construction.interfaces.cli select-demo \
  --source-data-root data/pmc-rct \
  --dest-data-root data/data_for_test/data_demo_1000 \
  --total 1000
```

检查选样结果：

```bash
wc -l data/data_for_test/data_demo_1000/manifest/files.jsonl
cat data/data_for_test/data_demo_1000/manifest/selection_summary.json
```

前台跑真实 LLM PI 抽取、离线 MeSH fallback 映射和本地索引构建；`--verbose` 会输出逐篇进度：

```bash
python -m ebm_backend.index_construction.interfaces.cli simplified \
  --source-data-root data/data_for_test/data_demo_1000 \
  --dest-data-root data/data_for_test/data_demo_1000 \
  --limit 1000 \
  --pi-mode llm \
  --mesh-mode offline \
  --workers 16 \
  --no-copy-source \
  --no-query-validation \
  --verbose
```

断点继续：中断后重跑同一条命令即可。不要加 `--force`，已有 `derived/*.json` 会被跳过并用于重建最终索引。

检查处理结果：

```bash
find data/data_for_test/data_demo_1000/derived -maxdepth 1 -name '*.json' | wc -l
wc -l data/data_for_test/data_demo_1000/index/local_rct_index.jsonl
```

1000 篇检索 smoke test：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --index-path data/data_for_test/data_demo_1000/index/local_rct_index.jsonl \
  --query "postoperative pain nerve block surgery" \
  --top-k 10
```

已验收样例：该 query 返回 10 条结果，Top1 为 `pmid:37360747`，标题为 `Erector Spinae Plane (ESP) Block for Postoperative Pain Management after Open Oncologic Abdominal Surgery`，命中 `title`、`population`、`intervention`、`mesh_terms`、`abstract` 等字段。

### 4. 可选：重新跑 100 篇 PI 抽取和索引

本地快速调通，不调用 LLM：

```bash
python -m ebm_backend.index_construction.interfaces.cli simplified \
  --source-data-root data/data_for_test/data_demo \
  --dest-data-root data/data_for_test/data_demo_with_mesh \
  --limit 100 \
  --pi-mode local \
  --workers 16 \
  --force
```

真实 LLM PI 抽取，失败时默认回退本地 PI，继续构建索引：

```bash
python -m ebm_backend.index_construction.interfaces.cli simplified \
  --source-data-root data/data_for_test/data_demo \
  --dest-data-root data/data_for_test/data_demo_with_mesh \
  --limit 100 \
  --pi-mode llm \
  --mesh-mode offline \
  --workers 16 \
  --force
```

如需严格观察 LLM 失败，不启用本地兜底：

```bash
python -m ebm_backend.index_construction.interfaces.cli simplified \
  --source-data-root data/data_for_test/data_demo \
  --dest-data-root data/data_for_test/data_demo_with_mesh \
  --limit 100 \
  --pi-mode llm \
  --mesh-mode offline \
  --workers 16 \
  --no-local-fallback \
  --force
```

## 推荐测试 query

以下 query 都来自当前 100 篇 demo 文章内容，可用于观察“检索 + 检索后输出”。

## 本地 score 计算方式

当前 `search-local` 的 `score` 来自 `LocalRCTIndex`，不是 Elasticsearch BM25。计算方式是 query token 与各字段 token 的重叠数乘以字段权重后求和；如果完整 query 字符串出现在字段中，会额外加一次该字段权重。

字段权重：

```text
title: 4.0
population: 3.0
intervention: 3.0
mesh_population: 2.5
mesh_intervention: 2.5
mesh_terms: 1.5
population_original: 2.0
intervention_original: 2.0
abstract: 1.0
```

因此，命中 `title`、`population`、`intervention`、`mesh_terms` 等多个字段的文章会排得更高。该 score 适合 demo 和调试，不包含 IDF、BM25 长度归一化或生产级排序策略。

### Query 1: Duloxetine / catheter-related bladder discomfort

命令：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --query "duloxetine catheter-related bladder discomfort" \
  --top-k 3
```

预期 top hit：

```json
{
  "study_id": "pmid:37877838",
  "title": "Duloxetine in Reducing Catheter-Related Bladder Discomfort: A Prospective, Randomized, Double-Blind, Placebo-Controlled Study",
  "population": "patients who underwent urinary catheterization",
  "intervention": "Duloxetine"
}
```

### Query 2: Garlic extract / hospitalized COVID-19

命令：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --query "garlic extract coronavirus hospitalized" \
  --top-k 3
```

预期 top hit：

```json
{
  "study_id": "pmid:36998289",
  "title": "Effectiveness of Fortified Garlic Extract Oral Capsules as Adjuvant Therapy in Hospitalized Patients with Coronavirus Disease 2019: A Triple-Blind Randomized Controlled Clinical Trial",
  "population": "Hospitalized Patients with Coronavirus Disease 2019",
  "intervention": "Fortified Garlic Extract Oral Capsules Adjuvant Therapy"
}
```

### Query 3: Epley maneuver / positional nystagmus

命令：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --query "Epley maneuver positional nystagmus" \
  --top-k 3
```

预期 top hit：

```json
{
  "study_id": "pmid:36923489",
  "title": "Comparison of the efficacy of the Epley maneuver and repeated Dix-Hallpike tests for eliminating positional nystagmus: A multicenter randomized study"
}
```

### Query 4: Zinc-carbonate hydroxyapatite / dental caries

命令：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --query "zinc-carbonate hydroxyapatite dental caries" \
  --top-k 3
```

预期 top hit：

```json
{
  "study_id": "pmid:36908720",
  "title": "Evaluation of remineralizing effect of zinc-carbonate hydroxyapatite on the reduction of postrestorative sensitivity: A randomized controlled clinical trial",
  "mesh_population": ["Dental Caries"]
}
```

### Query 5: ADHDCoach / parents / children with ADHD

命令：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --query "ADHDCoach parents children ADHD" \
  --top-k 3
```

预期 top hit：

```json
{
  "study_id": "pmid:36923370",
  "title": "ADHDCoach-a virtual clinic for parents of children with ADHD: Development and usability study",
  "population": "parents of children with ADHD",
  "intervention": "ADHDCoach-a virtual clinic for parents of children with ADHD"
}
```

### Query 6: Tranexamic acid / orthopedic surgery

命令：

```bash
python -m ebm_backend.index_construction.interfaces.cli search-local \
  --query "tranexamic acid orthopedic surgery" \
  --top-k 3
```

预期 top hit：

```json
{
  "study_id": "pmid:36919025",
  "title": "Empiric tranexamic acid use provides no benefit in urgent orthopedic surgery following injury",
  "population": "urgent orthopedic surgery following injury",
  "intervention": "Empiric tranexamic acid use"
}
```

## 2026-05-12 小样本真实 LLM smoke

本轮按真实联调计划只验证 Module 1 小样本建索引能力，不把该小索引用于后续 Module 2 / Module 3 检索：

```bash
PYTHONPATH=backend/src python -m ebm_backend.index_construction.interfaces.cli simplified \
  --source-data-root data/data_for_test/data_demo \
  --dest-data-root /tmp/ebm_real_llm_module1_demo \
  --limit 5 \
  --pi-mode llm \
  --mesh-mode offline \
  --no-copy-source \
  --top-k-search 3 \
  --verbose
```

结果：

- 5 篇 study 全部 indexed，`failed=0`
- `/tmp/ebm_real_llm_module1_demo/derived/*.json` 已生成
- `/tmp/ebm_real_llm_module1_demo/index/local_rct_index.jsonl` 已生成
- query validation 通过 `3/5`

注意：本轮发现并修复了 `--no-copy-source` 路径问题。此前 `copy_source=false` 时 runner 仍从 `dest_data_root/manifest/files.jsonl` 读取 manifest，导致新目标目录下报 `FileNotFoundError`；现在无复制模式会从 `source_data_root` 读取 manifest，并仍把 derived/index 写到 `dest_data_root`。

观察到的 LLM 行为：部分 PI extraction 返回空 span，触发默认本地 PI fallback 后继续导出和建索引。这符合当前 smoke 目标；如果要严格评估 LLM PI 质量，请加 `--no-local-fallback` 单独跑。

## 历史单篇真实 LLM smoke

以下命令仍可用于观察单篇真实 LLM PI 抽取链路。它会打开阶段输出，并给真实 LLM 请求设置 120 秒超时，便于判断当前卡在哪一步。

```bash
python - <<'PY'
from ebm_backend.index_construction.application import run_module1_demo_sync

result = run_module1_demo_sync(verbose=True, request_timeout=120)
print("study_id:", result.study_id)
print("export_path:", result.export_path)
print("population:", result.normalized.population.indexable_text[:300])
print("intervention:", result.normalized.intervention.indexable_text[:300])
print("mesh_terms:", result.document.mesh_terms)
PY
```

阶段输出会显示当前停在：study 入库、LLM PI 抽取、span 校验、MeSH 映射、index document 构建或派生 JSON 导出。

## 简化版目标产物

- `data/data_for_test/data_demo_with_mesh/`：100 篇样本目录
- `data/data_for_test/data_demo_1000/`：1000 篇主题簇样本目录
- 每篇 study 的 PI 抽取与映射结果
- 可检索的本地索引文件
- 固定 query 检索测试与通过结果

## 阶段输出解释

- `[module1-demo] saving study state`：正在写入/更新 PostgreSQL 的 `module1_studies`
- `[module1-demo] calling LLM for PI extraction`：正在调用 `.env` 中配置的 OpenAI-compatible Chat Completions API
- `[module1-demo] validating extracted spans`：正在检查 population/intervention span 是否非空且能在原文中定位
- `[module1-demo] normalizing PI and mapping MeSH terms`：正在清洗 PI、去重 span、拆分 concept，并调用 NLM MeSH Lookup；长 span 会先生成短语候选再做 MeSH 映射，查询失败时使用本地兜底词典，仍不能命中则保留原始 PI 文本继续索引
- `[module1-demo] building index document`：正在生成 ES index document 结构，本 demo 暂不写入真实 ES
- `[module1-demo] exported ...`：已导出 `data/data_for_test/data_demo/derived/*.json`
- `[module1-simplified] progress N/T (...)`：简化 runner 的逐篇进度；`ok` 是已成功生成 derived/index document 的篇数，`failed` 是失败篇数

如果长期停在 `calling LLM for PI extraction`，优先检查 `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`LLM_MODEL` 和代理端点响应时间。

## 预期结果

- 输出一个 `study_id`
- 输出一个 `data/data_for_test/data_demo/derived/*.json` 路径
- PostgreSQL 中 `module1_studies` 对应记录的：
  - `extraction_status = completed`
  - `normalization_status = completed`
  - `indexed_status = completed`

简化版完整预期结果：
- `data/data_for_test/data_demo_with_mesh/` 中有 100 篇 `primary_rct`
- `data/data_for_test/data_demo_1000/` 中有 1000 篇 `primary_rct`
- 100 篇样本均生成 PI 抽取和映射结果
- 1000 篇样本可生成对应 derived 和本地索引，用于后续 Module 3 调试
- 本地索引可完成检索
- 固定 query 检索测试通过

## 检查点

- `data/data_for_test/data_demo*/derived/` 下出现派生 JSON
- 派生 JSON 顶层字段顺序应为：`pi`、`extraction`、`normalized`、`document`、`study`，优先查看 `pi`
- `pi.population.spans` 和 `pi.intervention.spans` 不应出现完全重复的 span
- `module1_studies` 中该 study 的状态已更新
- MeSH 结果可在派生 JSON 的 `pi.*.mesh_terms`、`normalized.population.mesh_terms` / `normalized.intervention.mesh_terms` 和 `document.mesh_terms` 中查看
- 如果某篇文献的 `document.mesh_terms` 为空，说明当前 PI concept 没有命中 NLM MeSH 或本地兜底词典；此时 `population` / `intervention` 仍会使用原始 PI 与同义词参与检索，但召回扩展能力会弱，需要补充 MeSH 兜底词典或改进 concept 拆分
- 简化版可额外检查：
  - `data/data_for_test/data_demo_with_mesh/manifest/files.jsonl` 与文件目录一致
  - `data/data_for_test/data_demo_1000/manifest/files.jsonl` 与文件目录一致
  - 检索结果至少能召回预期 study
  - 索引输入字段包含 population / intervention / mesh terms
