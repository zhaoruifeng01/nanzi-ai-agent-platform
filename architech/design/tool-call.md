# 云枢智能体平台工具调用规范与格式文档

本文档详细描述了云枢智能体平台（Yunshu AI Agent Platform）在与大语言模型（LLM）交互时，工具调用（Tool Calling）的完整报文格式、交互协议及实现细节。

## 1. 整体架构概览

平台基于 **LangChain** 框架构建，兼容 **OpenAI Tool Call** 标准协议。工具的执行遵循 **ReAct (Reasoning and Acting)** 循环模式：
1. **思考 (Thought)**: 模型决定是否需要调用工具。
2. **行动 (Act)**: 模型输出结构化指令。
3. **观察 (Observe)**: 系统执行工具并返回结果。
4. **决策 (Finalize)**: 模型根据观察结果生成最终回答。

---

## 2. 工具定义格式 (Registration Format)

当模型实例启动并调用 `bind_tools` 时，系统会将工具元数据转换为 JSON Schema 发送给 LLM。

### 2.1 标准 JSON 结构
```json
{
  "type": "function",
  "function": {
    "name": "execute_sql_query",
    "description": "针对指定的数据源执行只读的 SQL SELECT 查询，并在指定的数据集权限范围内进行校验。",
    "parameters": {
      "type": "object",
      "properties": {
        "sql": {
          "type": "string",
          "description": "要执行的 SQL SELECT 查询语句。"
        },
        "data_source": {
          "type": "string",
          "description": "数据源标识符（如 'mysql_oa'），用于决定数据库连接和 SQL 方言。"
        },
        "dataset_name": {
          "type": "string",
          "description": "数据集名称（如 'energy_usage'），用于权限校验。"
        }
      },
      "required": ["sql", "data_source", "dataset_name"]
    }
  }
}
```

### 2.2 动态参数映射 (Dynamic Tools)
对于从数据库 `sys_api_tools` 加载的工具，系统会通过 `GenericApiToolFactory` 动态生成 Pydantic 模型，确保 `parameter_schema` 正确转换为上述 JSON 定义。

---

## 3. 交互报文协议 (Interaction Messages)

在多轮 ReAct 交互中，消息序列的完整结构如下：

| 角色 (Role) | 内容 (Content) | 附加字段 (Additional Fields) | 说明 |
| :--- | :--- | :--- | :--- |
| **system** | `system_prompt` | - | 包含 Agent 的人格定义和工作流约束。 |
| **user** | 用户提问内容 | - | 原始输入。 |
| **assistant** | `null` 或 思考文本 | `tool_calls: [...]` | 模型生成的工具调用请求，包含 `id`、`name` 和 `args`。 |
| **tool** | 工具执行结果 (JSON/Text) | `tool_call_id: "..."` | **关键字段**：必须与 `assistant` 消息中的 `id` 严格匹配。 |

### 报文示例 (以 ChatBI 为例)
```json
[
  { "role": "system", "content": "你是一个数据分析专家..." },
  { "role": "user", "content": "帮我查一下去年的能耗趋势" },
  {
    "role": "assistant",
    "content": "为了准确回答您的问题，我需要先了解能耗数据集的结构。",
    "tool_calls": [
      {
        "id": "call_qwer123",
        "type": "function",
        "function": {
          "name": "get_dataset_schema",
          "arguments": "{\"keywords\": \"energy\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_qwer123",
    "content": "{\"dataset\": \"energy_stats\", \"columns\": [\"usage\", \"time\"]}"
  }
]
```

---

## 4. 特殊模式：XML 兼容解析

针对部分未完全适配 OpenAI Tool Call 协议或在复杂 Prompt 下倾向于输出标签的模型（如 DeepSeek V3/R1 在某些配置下），平台在 `GeneralChatExecutor` 中实现了 XML 自动捕获。

**模型输出格式：**
```xml
<function_calls>
  <invoke name="execute_sql_query">
    <parameter name="sql">SELECT sum(usage) FROM energy_table</parameter>
    <parameter name="data_source">clickhouse_prod</parameter>
    <parameter name="dataset_name">energy_usage</parameter>
  </invoke>
</function_calls>
```

**处理逻辑：**
1. 正则或 `ElementTree` 识别 `<function_calls>` 代码块。
2. 提取 `invoke` 的 `name` 和 `parameter`。
3. 伪造一个 `tool_call_id` 并将其注入到标准的 LangChain 执行流中。

---

## 5. 核心逻辑实现参考

- **工具绑定**: `app/services/ai/executors/data_executor.py` 中的 `model_with_tools.bind_tools(tools)`。
- **动态实例化**: `app/services/ai/tools/generic_api.py` 的 `GenericApiToolFactory`。
- **隐式注入**: `app/services/ai/tools/registry.py` 的 `get_system_implicit_tools()`（如 `get_current_time`）。

---

## 6. 安全与权限 (Security)

在发送和执行过程中，平台会强制进行以下校验：
- **SQL 安全**: 使用 `sqlglot` 校验 AST，严禁非 SELECT 语句。
- **物理隔离**: 通过 `dataset_name` 在执行层强制进行用户权限校验，防止模型“越权”调用不属于当前用户的数据源。
- **SSRF 防御**: 通用 HTTP 工具会对 `url_template` 进行白名单和内部 IP 过滤。
```