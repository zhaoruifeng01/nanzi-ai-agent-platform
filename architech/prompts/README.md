# 云枢智能体平台 提示词管理 (Prompts Management)

本目录汇集了系统中所有涉及大语言模型（LLM）的提示词，便于统一管理、版本跟踪与优化。

## 目录结构

- [意图识别 (Intent Recognition)](intent_recognition.md): 用于 `IntentService` 的核心分类逻辑。
- [全局编排路由 (Orchestration Router)](orchestration_router.md): 用于 `RouterService` 的 Agent 智能分发逻辑。
- [元数据解析生成 (Metadata Generator)](metadata_generator.md): 用于 DDL/Markdown 解析的专用提示词。
- [智能体内部逻辑 (Internal Logic)](internal_logic.md): 包含 SQL 报错自愈（Self-Healing）与兜底说明逻辑。
- **[系统智能体提示词 (System Agents)](system_agents/)**:
    - [数据智能助手 (ChatBI)](system_agents/chatbi.md)
    - [元数据专家 (Metadata Specialist)](system_agents/metadata_specialist.md)
    - [知识库助手 (Knowledge Base)](system_agents/knowledge_base.md)
    - [通用对话助手 (General Chat)](system_agents/general_chat.md)

## 提示词调优说明
1. **ChatBI 提示词**: 必须包含 `dataset_menu` 的动态注入逻辑，确保模型感知 ClickHouse 表结构。
2. **路由提示词**: 应平衡“匹配精确度”与“兜底通用性”，避免过度路由至 ChatBI。
3. **自愈提示词**: 针对 SQL 错误提供即时反馈，降低幻觉导致的失败率。
