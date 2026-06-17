# 文档

`workflow_v3.md` 是当前分支维护中的 workflow 规范文档。

## 当前文档

- [Online EBM Workflow 规范](workflow_v3.md)
- [Backend 框架文档](../backend/README.md)
- [Online Pipeline Benchmark 文档](../benchmark/online_pipeline/README.md)

## 说明

历史架构、设计、指南和计划文档在当前分支中不再维护。

当前分支维护的后端接口边界是模块级 API，以及 benchmark 直接调用的内部 Python methods。workflow 级 HTTP API 和子任务级 HTTP API 不属于当前分支契约。
