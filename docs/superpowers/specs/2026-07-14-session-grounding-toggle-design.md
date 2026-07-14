# 会话级反幻觉开关设计

## 目标

在聊天“界面设置”和 AgentDebug 右侧“调试配置”中移除重复的模型选择控件，并在原位置放置“反幻觉校验”开关。开关默认关闭，按当前浏览器页面中的会话生效；刷新页面或开启新会话后恢复关闭。EmbedChat 与 AgentDebug 输入框中已有的模型选择保留。

## 行为边界

- 前端每次聊天请求都通过 `debug_options.grounding_enabled` 显式传递布尔值。
- 字段缺失、`false` 或非布尔真值均视为关闭，确保旧客户端默认不启用。
- 关闭时，Main、ChatBI、KnowledgeAgent 跳过 Grounding 审核、风险提示和 Knowledge 反思重试。
- 关闭不影响模型生成、工具调用、知识库检索、ChatBI SQL 执行、权限门禁或流式协议。
- 开启时完整复用当前意图优先 Grounding 策略。
- `hallucination_check` 继续作为 KnowledgeAgent 的深度模型评估选项；只有总开关开启时才可能生效。

## 实现结构

`BaseExecutor` 提供严格布尔判断 `_grounding_enabled()`，各 Runner 统一使用。Main 在关闭时不建立审核缓冲；ChatBI 的统一审计返回 PASS；KnowledgeAgent 在首次生成后直接输出，不调用评估器或规则重试。

前端 `ChatSettings.vue` 将模型选择区域替换为二段式开关。`EmbedChat.vue` 初始化 `enableGrounding: false`，发送请求时始终传递该值，并在开启新会话时重置为 `false`。AgentDebug 右侧 `DebugConfigPanel.vue` 同样用开关替换模型覆盖下拉框，由 `AgentDebug.vue` 的 `debugConfig.enableGrounding` 透传并在新建调试会话时复位；输入框模型选择继续维护 `debugConfig.model`。

## 验证

- Main：默认关闭无风险提示；显式开启仍产生既有提示。
- ChatBI：关闭时不追加风险提示；开启时保持原行为。
- KnowledgeAgent：关闭时只生成一次且不调用幻觉评估器；开启时保留反思循环。
- 前端：静态交互测试确认模型选择已移除、开关默认关闭、请求显式透传以及新会话重置。
- 执行相关 pytest、前端脚本测试、TypeScript 构建、`py_compile` 和 `git diff --check`；不运行 `./dev.sh`。
