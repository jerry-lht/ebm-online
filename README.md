# EBM Online Pipeline

自动化循证医学 (Evidence-Based Medicine) Pipeline，从临床问题出发，自动完成文献检索、筛选、数据抽取、Meta 分析和 GRADE 评估。

## 快速开始

### 环境要求

- Python 3.10+
- Git
- PostgreSQL 14+
- Redis 7+（Phase 5 需要）
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
cp config/.env.example .env
# 编辑 .env，将 sk-your-key-here 替换为你的真实 OPENAI_API_KEY
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

Redis 和 Elasticsearch 在后续 Phase 需要时再安装：

```bash
# Redis（Phase 5 需要）
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
python3 -c "from src.storage.db import init_db; from config.settings import settings; init_db(settings.database_url)"
```

### 7. 验证安装

```bash
# 配置加载（需要先创建 .env）
python3 -c "from config.settings import settings; print(settings.model_dump_json(indent=2))"

# 运行测试
python3 -m pytest tests/ -v
```

期望结果：配置正常输出 JSON，8 个测试全部通过。

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
├── frontend/            # Streamlit 前端
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
| 数据库 | PostgreSQL |
| 统计计算 | NumPy + SciPy |
| 前端 | Streamlit |

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
- [Module 2 详细设计](docs/module2-detail-design.md)
- [Module 3 详细设计](docs/module3-detail-design.md)
- [实现计划](docs/implementation-plan.md)
