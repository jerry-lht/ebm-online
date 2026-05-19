# Phase 0 测试文档

- **Status:** archived
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** Historical record only; not maintained.

> Archived Notice
> - Archived Date: 2026-05-15
> - Replacement: [docs/guides/phase5-api-test-guide.md](../../guides/phase5-api-test-guide.md), [docs/guides/phase6-gradio-demo-guide.md](../../guides/phase6-gradio-demo-guide.md)
> - Maintenance: No longer maintained; kept for traceability only.


本文档描述 Phase 0（项目骨架 & 基础设施）的完整验证步骤。

---

## 前置条件

- Python 3.10+ 已安装
- 已完成 README.md 中的步骤 1-4（克隆、虚拟环境、安装依赖、配置 .env）

### 虚拟环境和依赖安装

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 如果报 "No module named pip"（ensurepip 不可用的环境）：
python3 -m pip install --target=.venv/lib/python3.10/site-packages pip
.venv/bin/python3 -m pip install -r requirements.txt
```

### 创建 .env 文件

```bash
# 编辑根目录 .env，将 sk-your-key-here 替换为真实的 OPENAI_API_KEY
# 不创建 .env 会导致 "Field required" 报错（openai_api_key 为必填）
```

---

## 测试 1: 服务安装与启动

### 1.1 PostgreSQL

**安装：**

```bash
apt install -y postgresql postgresql-client
```

**启动：**

```bash
service postgresql start
```

**验证：**

```bash
pg_isready
```

期望输出：

```
/var/run/postgresql:5432 - accepting connections
```

**创建用户和数据库：**

```bash
su - postgres -c "psql -c \"CREATE USER ebm WITH PASSWORD 'ebm123';\""
su - postgres -c "psql -c \"CREATE DATABASE ebm_online OWNER ebm;\""
```

**验证连接：**

```bash
PGPASSWORD=ebm123 psql -h localhost -U ebm -d ebm_online -c "SELECT 1"
```

期望输出：

```
 ?column?
----------
        1
(1 row)
```

### 1.2 Redis

**安装：**

```bash
apt install -y redis-server
```

**启动：**

```bash
service redis-server start
```

**验证：**

```bash
redis-cli ping
```

期望输出：

```
PONG
```

### 1.3 Elasticsearch

**安装：**

```bash
apt update
apt install -y apt-transport-https ca-certificates curl gnupg

curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch \
  | gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" \
  > /etc/apt/sources.list.d/elastic-8.x.list

apt update
apt install -y elasticsearch
```

**配置（关闭安全认证，开发模式，只需执行一次）：**

```bash
# 关闭安全和 SSL
sed -i 's/^xpack.security.enabled: true/xpack.security.enabled: false/' /etc/elasticsearch/elasticsearch.yml
sed -i 's/^xpack.security.enrollment.enabled: true/xpack.security.enrollment.enabled: false/' /etc/elasticsearch/elasticsearch.yml
sed -i '/xpack.security.http.ssl:/,/keystore.path: certs\/http.p12/{s/enabled: true/enabled: false/}' /etc/elasticsearch/elasticsearch.yml
sed -i '/xpack.security.transport.ssl:/,/truststore.path: certs\/transport.p12/{s/enabled: true/enabled: false/}' /etc/elasticsearch/elasticsearch.yml

# 删除 cluster.initial_master_nodes（和 single-node 模式冲突）
sed -i '/^cluster.initial_master_nodes/d' /etc/elasticsearch/elasticsearch.yml

# 添加单节点模式（先检查是否已存在，避免重复）
grep -q "^discovery.type: single-node" /etc/elasticsearch/elasticsearch.yml || \
  echo -e "\ndiscovery.type: single-node\nxpack.security.enabled: false" >> /etc/elasticsearch/elasticsearch.yml
```

**启动：**

```bash
su - elasticsearch -s /bin/bash -c "/usr/share/elasticsearch/bin/elasticsearch -d -p /tmp/es.pid"
```

注意：
- ES 启动需要 15-30 秒，请等待后再验证
- 如果报 "already running" 相关错误，说明 ES 已经在跑了，直接验证即可
- 配置命令只需首次安装后执行一次，重复执行会导致字段重复报错

**验证（ES 启动较慢，等待 30-60 秒）：**

```bash
curl -s http://localhost:9200
```

期望输出（JSON 格式）：

```json
{
  "name": "...",
  "cluster_name": "elasticsearch",
  "version": {
    "number": "8.x.x"
  },
  "tagline": "You Know, for Search"
}
```

---

## 测试 2: 配置系统

### 步骤

```bash
python3 -c "from ebm_backend.shared.config.settings import settings; print(settings.model_dump_json(indent=2))"
```

### 期望结果

```json
{
  "openai_api_key": "sk-your-key-here",
  "openai_base_url": "https://api.openai.com/v1",
  "llm_model": "gpt-5.2",
  "llm_temperature": 0.0,
  "es_host": "http://localhost:9200",
  "redis_url": "redis://localhost:6379/0",
  "database_url": "postgresql://ebm:ebm123@localhost:5432/ebm_online",
  "llm_input_price_per_1m": 2.0,
  "llm_output_price_per_1m": 8.0
}
```

---

## 测试 3: 数据库初始化

### 步骤

```bash
python3 -c "from ebm_backend.shared.persistence.db import init_db; from ebm_backend.shared.config.settings import settings; init_db(settings.database_url); print('OK')"
```

### 验证表已创建

```bash
PGPASSWORD=ebm123 psql -h localhost -U ebm -d ebm_online -c "\dt"
```

### 期望结果

```
 Schema |     Name      | Type  | Owner
--------+---------------+-------+-------
 public | llm_cache     | table | ebm
 public | llm_usage     | table | ebm
 public | pipeline_runs | table | ebm
```

### 验证表结构（可选）

```bash
PGPASSWORD=ebm123 psql -h localhost -U ebm -d ebm_online -c "\d pipeline_runs"
PGPASSWORD=ebm123 psql -h localhost -U ebm -d ebm_online -c "\d llm_cache"
PGPASSWORD=ebm123 psql -h localhost -U ebm -d ebm_online -c "\d llm_usage"
```

---

## 测试 4: 模块导入

### 步骤

```bash
python3 -c "
import ebm_backend.online_pipeline.application.run_pipeline
import ebm_backend.online_pipeline.infrastructure.pipeline_repository
import ebm_backend.index_construction.application.retrieval
import ebm_backend.index_construction.application.classification
import ebm_backend.index_construction.application.extraction
import ebm_backend.index_construction.application.indexing
import ebm_backend.online_pipeline.application.question_study.expansion
import ebm_backend.online_pipeline.application.question_study.query_gen
import ebm_backend.online_pipeline.application.question_study.search
import ebm_backend.online_pipeline.application.evidence_analysis.screening
import ebm_backend.online_pipeline.application.evidence_analysis.planning
import ebm_backend.online_pipeline.application.evidence_analysis.extraction
import ebm_backend.online_pipeline.application.evidence_analysis.rob
import ebm_backend.online_pipeline.application.evidence_analysis.aggregation
import ebm_backend.online_pipeline.application.evidence_analysis.grade
import ebm_backend.shared.llm.gateway
import ebm_backend.shared.llm.tracker
import ebm_backend.shared.llm.cache
import ebm_backend.shared.llm.pricing
import ebm_backend.shared.statistics.engine
import ebm_backend.shared.statistics.effects
import ebm_backend.shared.statistics.pooling
import ebm_backend.shared.statistics.heterogeneity
import ebm_backend.shared.statistics.derivation
import ebm_backend.shared.statistics.corrections
import ebm_backend.shared.persistence.db
import ebm_backend.shared.persistence.models
import ebm_backend.shared.persistence.es_client
import ebm_backend.online_pipeline.interfaces.api.main
import ebm_backend.online_pipeline.interfaces.api
print('All imports OK')
"
```

### 期望结果

```
All imports OK
```

---

## 测试 5: 自动化测试套件

### 步骤

```bash
python3 -m pytest tests/ -v
```

### 期望结果

```
tests/unit/test_db.py::test_schemas_are_valid_sql PASSED
tests/unit/test_db.py::test_schema_defines_pipeline_runs PASSED
tests/unit/test_db.py::test_schema_defines_llm_cache PASSED
tests/unit/test_db.py::test_schema_defines_llm_usage PASSED
tests/unit/test_db.py::test_init_db_creates_tables PASSED
tests/unit/test_db.py::test_init_db_is_idempotent PASSED
tests/unit/test_settings.py::test_settings_loads_from_env PASSED
tests/unit/test_settings.py::test_settings_custom_values PASSED

8 passed
```

注：如果 PostgreSQL 未运行，`test_init_db_*` 会显示 SKIPPED 而非 FAILED。

---

## 测试 6: 数据完整性

### 步骤

```bash
# 验证 PMC RCT 数据存在
ls data/pmc-rct/

# 统计文件数量
find data/pmc-rct -name "*.json" | wc -l
```

### 期望结果

- 目录包含 2023/, 2024/, 2025/, 2026/, manifest/
- JSON 文件总数约 67,501

---

## 故障排查

### PostgreSQL 连接失败

```bash
# 检查服务状态
service postgresql status

# 重启
service postgresql restart

# 查看日志
tail -20 /var/log/postgresql/postgresql-14-main.log
```

### Redis 连接失败

```bash
# 检查服务状态
service redis-server status

# 重启
service redis-server restart

# 查看日志
tail -20 /var/log/redis/redis-server.log
```

### Elasticsearch 启动失败

```bash
# 检查服务状态
service elasticsearch status

# 查看日志
tail -30 /var/log/elasticsearch/elasticsearch.log

# 常见问题：内存不足，调小 JVM heap
# 编辑 /etc/elasticsearch/jvm.options.d/heap.options
echo "-Xms512m" > /etc/elasticsearch/jvm.options.d/heap.options
echo "-Xmx512m" >> /etc/elasticsearch/jvm.options.d/heap.options
service elasticsearch restart
```

### 端口冲突

```bash
# 查看端口占用
ss -tlnp | grep -E '5432|6379|9200'
```

如果端口被占用，停掉占用进程或修改 `.env` 中的连接地址。
