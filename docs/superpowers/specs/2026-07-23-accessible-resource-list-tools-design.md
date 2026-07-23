# Design: 可访问数据集 / 知识库列表系统工具

**Date:** 2026-07-23  
**Status:** Approved (方案 1)

## Goal

新增两个平台内置系统级工具，供 Agent 按需列出**当前用户有权限**的轻量资源目录（不含表/字段/指标等重内容），并经 `get_system_implicit_tools()` 自动注入所有 Runner。

## Tools

| Name | Purpose |
|------|---------|
| `list_accessible_datasets` | 列出有权限的 ChatBI 元数据数据集 |
| `list_accessible_knowledge_bases` | 列出有权限的知识库（RAGFlow Dataset） |

- 无必填参数
- 返回 JSON 字符串：`{"items": [...], "count": N}`
- 无用户上下文 / 失败时返回可读错误文案

## Fields

**Dataset item:** `id`, `name`, `display_name`, `description`, `status`  
**Knowledge base item:** `ragflow_dataset_id`, `name`, `description`, `notes`, `visibility`, `owner`

## Permission

- Datasets: `MetadataService.list_accessible_dataset_options`（与门户 accessible 接口一致）
- Knowledge bases: `PermissionService.get_knowledge_base_access` + `KnowledgeBaseMetadata`（admin 全量；否则权限并集 + 自建 + 默认公开 KB）

## Injection

- 注册到 `ToolRegistry._registry`
- 加入 `get_system_implicit_tools()`（与 `memory_search` 同类）
- `agent_prompts` 工具说明表补充触发场景

## Out of scope

- 分页 / keyword 过滤（轻量字段，量可控）
- 返回表结构、字段、metrics、chunk 内容
- 管理端开关
