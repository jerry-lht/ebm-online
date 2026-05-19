# Online EBM Pipeline — 实施状态快照

- **Status:** active
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** 当前实现状态与近期执行优先级以本文档为准。

## 目标

本轮只做文档层收敛：保证入口可信、状态一致、过时信息隔离，降低后续维护成本。

## 当前状态快照

### 代码结构（当前口径）

- 后端主代码：`backend/src/ebm_backend/`
- 在线主链路：`backend/src/ebm_backend/online_pipeline/`
- 索引构建链路：`backend/src/ebm_backend/index_construction/`
- 共享能力：`backend/src/ebm_backend/shared/`
- 测试：`tests/`

### 数据与索引（当前口径）

- 演示数据根目录：`data/data_for_test/`
- 1000 篇主链路样本：`data/data_for_test/data_demo_1000/`
- 本地索引默认路径：`data/data_for_test/data_demo_1000/index/local_rct_index.jsonl`

### 可运行主链路（当前）

- Phase 5 API：见 `docs/guides/phase5-api-test-guide.md`
- Phase 6 Gradio Demo：见 `docs/guides/phase6-gradio-demo-guide.md`

### 文档集分级（第一轮）

- `active`
  - `docs/README.md`
  - `docs/plans/implementation-plan.md`
  - `docs/guides/phase5-api-test-guide.md`
  - `docs/guides/phase6-gradio-demo-guide.md`
- `reference`
  - `docs/architecture/*`
  - `docs/design/*`
  - `docs/guides/phase2-demo-test-guide.md`
  - `docs/guides/module2-test-guide.md`
  - `docs/guides/module3-test-guide.md`
- `archived`
  - `docs/archive/*`

## 下一步待办（文档）

1. 为 `reference` 文档补齐状态头与路径口径（特别是 `src/...` 旧路径示例）。
2. 合并重复测试命令模板，压缩 Module2/3 与 Phase2 的重复操作段落。
3. 对 `docs/design/module1-detail-design.md` 中历史表述分层：保留设计意图，迁移执行流水到归档。

## 已完成（本轮）

- `docs/README.md` 收敛为唯一入口。
- 建立 `docs/archive/`，并迁移 `phase0-test-guide`、`phase1-test-guide`。
- 确认当前路径口径以 `backend/src/ebm_backend/...` 与 `data/data_for_test/...` 为准。

## 不再使用的旧路径口径（禁止新增）

- `src/orchestrator/`
- `src/api/`
- 不带前缀的裸路径（例如 `data_demo_with_mesh/...`）
