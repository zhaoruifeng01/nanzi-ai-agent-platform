# Accessible Resource List Tools Implementation Plan

> **For agentic workers:** Execute inline with test-first checkpoints.

**Goal:** 新增 `list_accessible_datasets` / `list_accessible_knowledge_bases` 系统隐式工具，按权限返回轻量目录。

**Architecture:** 薄工具门面 + 复用 `MetadataService.list_accessible_dataset_options` 与 `PermissionService.get_knowledge_base_access`；经 ToolRegistry 注册并自动注入。

**Tech Stack:** Python, `@tool` / tool_compat, AsyncSessionLocal, pytest

---

### Task 1: 工具行为单测（先红）

**Files:**
- Create: `tests/ai/tools/test_resource_catalog_tools.py`
- Modify: `tests/ai/executors/test_system_tools_injection.py`

- [ ] 无用户上下文返回错误
- [ ] 数据集工具映射轻量字段并返回 count
- [ ] 知识库工具按 access 过滤并返回约定字段
- [ ] 两者出现在 `get_system_implicit_tools()` 与 `_registry`

### Task 2: 实现工具并注册

**Files:**
- Create: `app/services/ai/tools/resource_catalog_tools.py`
- Modify: `app/services/ai/tools/registry.py`
- Modify: `app/services/ai/agent_prompts.py`
- Modify: `tests/CHECKLIST.md`

- [ ] 实现两个 async `@tool`
- [ ] 注册 + 隐式注入
- [ ] 提示词一行说明
- [ ] 更新 CHECKLIST
