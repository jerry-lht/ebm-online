# Documentation Entry (Single Source)

- **Status:** active
- **Last Reviewed:** 2026-05-15
- **Source of Truth:** This file is the only global docs entrypoint.

## 文档状态标签规范

- `active`: 当前主链路必须维护，变更后优先更新。
- `reference`: 设计或历史实现参考，不保证与当前代码完全同步。
- `archived`: 历史记录，不再维护；仅用于追溯。

## 当前架构

- [实现状态快照与待办](plans/implementation-plan.md) (`active`)
- [高层架构设计](architecture/architecture-design.md) (`reference`)
- [共享基础设施设计](architecture/shared-infrastructure-design.md) (`reference`)
- [数据流水线设计](design/data-pipeline-for-online-ebm.md) (`reference`)

## 当前可运行链路

- [Phase 5 API 测试指南](guides/phase5-api-test-guide.md) (`active`)
- [Phase 6 Gradio Demo 测试指南](guides/phase6-gradio-demo-guide.md) (`active`)
- [Phase 2 Demo 测试指南](guides/phase2-demo-test-guide.md) (`reference`)
- [Module 2 简化版测试指南](guides/module2-test-guide.md) (`reference`)
- [Module 3 简化版测试指南](guides/module3-test-guide.md) (`reference`, 与当前实现行为对齐，含并发与降级测试说明)

## 历史归档

- [归档目录](archive/README.md)
- [Phase 0 测试文档（归档）](archive/guides/phase0-test-guide.md)
- [Phase 1 测试文档（归档）](archive/guides/phase1-test-guide.md)

## 维护规则

- 所有文档头部必须声明：`Status`、`Last Reviewed`、`Source of Truth`。
- 除 `docs/README.md` 外，其他文档不再维护全局目录。
- 路径示例统一使用仓库真实路径（例如 `backend/src/ebm_backend/...`、`data/data_for_test/...`）。
