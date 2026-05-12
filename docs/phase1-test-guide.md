# Phase 1 测试文档

本文档用于逐步验证 Phase 1 的共享基础设施。

---

## 1 前置条件

- Python 3.10+
- 已安装 `requirements.txt`
- 已配置根目录 `.env`，至少包含 `OPENAI_API_KEY`
- PostgreSQL 可用时执行数据库测试；不可用则相关测试会跳过

---

## 2 目标范围

本阶段验证以下内容：

- `LLMGateway` 基础调用链
- `CacheManager` 的命中、写入、失效
- `UsageTracker` 的调用记录和聚合查询
- `StatsEngine` 的 effect / pooling / heterogeneity / derivation

不在本阶段验证：

- Rate Limiter
- Retry Logic
- Module 1/2/3 的完整业务流程

---

## 3 建议执行顺序

### 步骤 1: 配置检查

```bash
python3 -c "from ebm_backend.shared.config.settings import settings; print(settings.llm_model, settings.database_url)"
```

期望：
- 正常输出模型名和数据库 URL

### 步骤 2: 单元测试总跑

```bash
python3 -m pytest tests/unit -q
```

期望：
- 全部通过

### 步骤 3: 逐模块验证

#### 3.1 数据库 schema

```bash
python3 -m pytest tests/unit/test_db.py -q
```

期望：
- PostgreSQL 可用时通过
- 不可用时与数据库相关测试跳过

#### 3.2 LLM 基础设施

```bash
python3 -m pytest tests/unit/test_llm_infra.py -q
```

期望：
- cache round-trip 通过
- usage 聚合通过
- gateway 二次调用命中缓存

#### 3.3 统计引擎

```bash
python3 -m pytest tests/unit/test_stats_engine.py -q
```

期望：
- MD 计算通过
- pooling 通过
- heterogeneity 通过

#### 3.4 Cochrane datapackage 对照

```bash
python3 - <<'PY'
import csv, io, math, zipfile
from pathlib import Path
from ebm_backend.shared.statistics.effects import StudyData, compute_smd, compute_log_or

zip_path = Path('data/Cochrane/original-data/data-package/CD015064-dataPackage.zip')
with zipfile.ZipFile(zip_path) as z:
    with z.open('CD015064-analysis-data/CD015064-data-rows.csv') as f:
        rows = list(csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig')))

cont = next(r for r in rows if r['Analysis number'] == '1' and r['Study'] == 'EUCTR2004-002688-25-GB')
res_c = compute_smd(StudyData(
    study_id=cont['Study'],
    outcome_type='continuous',
    exp_mean=float(cont['Experimental mean']),
    exp_sd=float(cont['Experimental SD']),
    exp_n=int(cont['Experimental N']),
    ctrl_mean=float(cont['Control mean']),
    ctrl_sd=float(cont['Control SD']),
    ctrl_n=int(cont['Control N']),
))
print(round(res_c.effect, 6), round(res_c.ci_low, 6), round(res_c.ci_high, 6))
print(cont['Mean'], cont['CI start'], cont['CI end'])

binrow = next(r for r in rows if r['Analysis number'] == '1' and r['Study'] == 'Wahn 2002')
res_b = compute_log_or(StudyData(
    study_id=binrow['Study'],
    outcome_type='binary',
    exp_events=int(binrow['Experimental cases']),
    exp_n=int(binrow['Experimental N']),
    ctrl_events=int(binrow['Control cases']),
    ctrl_n=int(binrow['Control N']),
))
print(round(math.exp(res_b.effect), 6), round(math.exp(res_b.ci_low), 6), round(math.exp(res_b.ci_high), 6))
print(binrow['Mean'], binrow['CI start'], binrow['CI end'])
PY
```

期望：
- 连续型样例的 effect / CI 与 CSV 基本一致
- 二分类样例的 OR / CI 与 CSV 一致
- 允许最后几位小数有四舍五入误差

---

## 4 手动检查项

### 4.1 Cache 行为

检查内容：
- `screening / extraction / rob` 才会进入缓存
- 相同 `task_type + inputs + prompt_version` 命中缓存
- `invalidate_by_study` 能按 `study_id` 删除
- 生产主线以 PostgreSQL 为准；SQLite 仅用于单元测试和本地适配

### 4.2 Usage 行为

检查内容：
- 每次调用都写入 `llm_usage`
- `run_id` 能聚合出总 token / 总费用 / 总耗时
- `module` 能做分组查询

### 4.3 Stats 行为

检查内容：
- 连续变量可计算 MD
- 统计转换函数可返回可用结果
- pooled effect、Q、I² 在单测中稳定

---

## 5 当前已知约束

- `openai` 在测试环境缺失时，gateway 仍可被 mock 测试导入
- PostgreSQL 旧表若缺少 `cache_key`，`init_db` 会自动补迁移
- Phase 1 不含限流和重试，后续是否补充按需求决定
- Cochrane datapackage 的单 study 样例已对照通过，stats 公式和原始数据一致
