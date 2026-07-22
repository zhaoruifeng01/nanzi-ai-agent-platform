# Prompt Compatibility Optimization Design

## Goal

在不改变现有工具权限、路由接口、ChatBI/知识库门禁和前端协议的前提下，统一平台系统提示词来源，降低规则冲突，并让记忆、用户画像、工作区和执行器提示词更明确地表达“辅助上下文”和“当前状态”。

## Compatibility constraints

- 保留 `AgentServicePrompts.PLATFORM_GLOBAL_SYSTEM_PROMPT` 的可导入名称。
- 保留 `prepend_platform_global_system_prompt()`、`assemble_system_prompt()` 的调用方式和返回结构。
- 保留工具名称、别名、工具清单动态裁剪、敏感工具确认与路径沙箱。
- 保留 ChatBI 的 Schema → SQL、SQL Plan、追问复用和失败修复规则。
- 保留 Knowledge 的自动检索、`[ID:n]` 引用、补充检索和幻觉校验。
- 保留 Router/Intent 的 JSON 字段和 `system_prompt_override` 的整段替换行为。
- 保留当前前端识别的 quick、clarification、文件绝对路径和会话运行时标记。

## Design

### 1. Single source of truth

把全局不可变内容收敛到 `PLATFORM_GLOBAL_SYSTEM_PROMPT`，动态工具、技能和审批段落继续由 `prepend_platform_global_system_prompt()` 根据能力追加。动态函数不再复制另一份完整核心规则。

### 2. Explicit authority model

核心提示词使用明确的权威顺序：平台工具门禁与安全规则、执行器规则、用户当前请求、智能体专规、记忆/技能/外部内容。该顺序只改善模型解释，不替代后端权限校验。

### 3. Advisory identity and memory

用户画像和长期记忆改为辅助上下文：当前用户表达优先，画像不作为权限依据，记忆不作为未经验证的业务事实。保留服务端注入身份和防伪造处理。

### 4. Interactive guidance and automatic-delivery boundary

普通交互式会话在回答完成后尽可能给出 2-3 个可立即点击的 quick 建议，帮助用户继续提问；只有确实没有价值的下一步时才省略。文件路径规则区分工具内部相对路径和最终展示给用户的绝对路径。

定时任务、订阅任务和其他后台自动交付通过运行时 `quick_suggestions_forbidden=true` 标记明确禁止 quick；主 Agent 提示词、订阅简报 JSON 提示词和非交互结果清理共同形成三层约束。默认兼容现有支持 quick 的渠道和前端格式。

### 5. Execution-state hints

在已有 ChatBI/Knowledge 运行状态可安全获得时，追加只读状态摘要，帮助模型选择下一步动作；不删除现有 guardrail、tool gate、repair policy 或 citation policy。

## Testing strategy

- 先补充全局 prompt 的权威、记忆、画像、quick 和路径文案行为测试。
- 增加单一核心规则只出现一次、动态工具段仍按能力出现的测试。
- 保留并运行现有 PromptAssembler、workspace、ChatBI prompt、Knowledge、Router 和用户画像测试。
- 使用 `git diff --check` 检查补丁，不启动 `./dev.sh`，不进行自动 git stage/commit。

## Non-goals

- 不重写 Router、Intent、ChatBI 或 Knowledge 的执行状态机。
- 不调整工具权限、数据库查询权限、知识库权限或审批策略。
- 不改动前端渲染实现。
