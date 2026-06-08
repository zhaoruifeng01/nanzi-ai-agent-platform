import time
import uuid
import json
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
from datetime import datetime

from app.services.ai.runtime.agentscope.compat import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from app.schemas.agent import ChatConfig, AgentExecutionStep
from app.services.ai.tools.registry import ToolRegistry
from app.services.ai.config import AgentConfigProvider
from app.services.ai.executors.base import BaseExecutor
from app.services.ai.executors.common import (
    convert_history_to_messages,
    extract_tokens_from_message,
    normalize_messages_for_llm,
    tools_include_named,
    MODEL_STREAM_MAX_RETRIES,
    build_stream_retry_log,
    build_stream_error_log,
    is_retryable_stream_error,
)
from app.services.ai.executors.prompts import GeneralChatPrompts
from app.services.ai.runtime.agentscope.chat import compat_to_runtime_messages, to_agentscope_messages
from app.services.ai.runtime.agentscope.tools import RuntimeToolSpec, runtime_tool_spec_from_legacy_tool
from app.services.ai.runtime.agentscope.tools import build_toolkit
from app.services.ai.turn_classifier import TurnType

logger = logging.getLogger(__name__)


class GeneralAgentRunner(BaseExecutor):
    def __init__(
        self,
        config: ChatConfig,
        trace_id: str,
        trace_buffer: List[AgentExecutionStep],
        debug_options: Dict[str, Any] = None,
        user_info: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        route_hints: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(config, trace_id, trace_buffer, debug_options, user_info, conversation_id)
        self.intent_info = None
        self.intent_elapsed_ms = 0.0
        self.turn_classification = None
        self._requires_knowledge_search = False
        self.route_hints = route_hints or {}

    async def execute(
        self,
        history: List[Dict[str, str]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        from app.services.ai.multimodal_support import (
            ensure_multimodal_compatible,
            resolve_runtime_model_name,
        )

        model_name = resolve_runtime_model_name(self.config, prefer_synthesis=True)
        incompatible_msg = await ensure_multimodal_compatible(history, model_name)
        if incompatible_msg:
            yield {"content": incompatible_msg, "status": "error"}
            return

        # 1. Prepare LLM
        configured_tools = self.config.tools or []
        tools = []
        if configured_tools:
            tools = await ToolRegistry.get_runtime_tools(configured_tools)

        system_tools = ToolRegistry.get_system_implicit_tools()
        if system_tools:
            tools.extend(
                runtime_tool_spec_from_legacy_tool(tool, source_type="system")
                for tool in system_tools
            )

        if self._requires_knowledge_search or (
            getattr(self, "turn_classification", None)
            and self.turn_classification.turn_type == TurnType.KNOWLEDGE
        ):
            self._requires_knowledge_search = True

        if self._requires_knowledge_search and not tools_include_named(tools, "search_knowledge_base"):
            kb_tool = await ToolRegistry.get_runtime_tool("search_knowledge_base")
            if kb_tool:
                tools.append(kb_tool)

        # 2. Build Messages
        system_content = self.config.system_prompt or ""
        route_hint = GeneralChatPrompts.route_hints(self.route_hints)
        if route_hint:
            system_content = f"{route_hint}\n\n{system_content}"
        if self._requires_knowledge_search:
            system_content = f"{GeneralChatPrompts.KNOWLEDGE_TURN_SYSTEM_HINT}\n\n{system_content}"
        runtime_messages = [SystemMessage(content=system_content)]
        runtime_messages.extend(convert_history_to_messages(history))
        runtime_messages = normalize_messages_for_llm(runtime_messages)

        # 3. Execution Mode Selection
        if not tools:
            # --- Simple Mode (No Tools) ---
            start_synthesis = time.time()
            yield {"type": "log", "id": f"syn_s_{uuid.uuid4().hex[:8]}", "title": "📝 准备回答", "details": "正在生成回答...", "status": "success"}
            
            # Use Synthesizer for simple mode
            llm = await AgentConfigProvider.get_synthesis_llm(streaming=True, config=self.config)
            
            full_content = ""
            content_emitted = False
            accumulated_msg = None
            stream_succeeded = False
            for stream_attempt in range(MODEL_STREAM_MAX_RETRIES):
                accumulated_msg = None
                try:
                    async for chunk in llm.astream(normalize_messages_for_llm(runtime_messages)):
                        if accumulated_msg is None:
                            accumulated_msg = chunk
                        else:
                            accumulated_msg += chunk
                        if chunk.content:
                            if not content_emitted:
                                yield {"type": "log", "id": f"gen_s_{uuid.uuid4().hex[:8]}", "title": "✨ 开始生成回复", "status": "success"}
                            content_emitted = True
                            full_content += chunk.content
                            yield {"content": chunk.content}
                    stream_succeeded = True
                    break
                except Exception as stream_err:
                    logger.error(
                        f"[GeneralAgentRunner] Simple mode stream failed "
                        f"(attempt {stream_attempt + 1}/{MODEL_STREAM_MAX_RETRIES}): {stream_err}"
                    )
                    if (
                        stream_attempt < MODEL_STREAM_MAX_RETRIES - 1
                        and not content_emitted
                        and is_retryable_stream_error(stream_err)
                    ):
                        yield build_stream_retry_log(stream_err, stream_attempt)
                        await asyncio.sleep(2 ** stream_attempt)
                        continue
                    yield build_stream_error_log(stream_err)
                    return
            if not stream_succeeded:
                return
            
            tokens = extract_tokens_from_message(accumulated_msg)
            
            # Record final answer as a trace step
            self._increment_step()
            self.trace_buffer.append(AgentExecutionStep(
                step_number=self.step_counter,
                event_type="synthesis",
                agent_name=self.config.agent_name,
                model=self.config.model_name,
                temperature=self.config.temperature,
                tool_output={"content": full_content},
                raw_log=full_content,
                execution_time_ms=(time.time() - start_synthesis) * 1000,
                prompt_tokens=tokens["prompt_tokens"],
                completion_tokens=tokens["completion_tokens"],
                total_tokens=tokens["total_tokens"],
                timestamp=datetime.fromtimestamp(start_synthesis)
            ))
            return

        # --- ReAct Mode (With Tools) ---
        from app.services.config_service import ConfigService
        max_steps_str = await ConfigService.get("agent_max_iterations")
        MAX_STEPS = int(max_steps_str) if max_steps_str else 5

        from app.services.ai.memory_recall_policy import (
            MEMORY_SEARCH_CORRECTION_MSG,
            last_user_message_text,
            looks_like_cross_session_recall_query,
            tools_include_memory_search,
        )
        from app.services.memory_config_service import MemoryConfigService

        memory_search_available = tools_include_memory_search(tools)
        recall_query_pending = False
        if memory_search_available:
            try:
                enabled = await MemoryConfigService.get_bool("memory_service_enabled", True)
                recall_query_pending = enabled and looks_like_cross_session_recall_query(
                    last_user_message_text(history)
                )
            except Exception:
                recall_query_pending = looks_like_cross_session_recall_query(
                    last_user_message_text(history)
                )

        knowledge_search_pending = (
            self._requires_knowledge_search
            and tools_include_named(tools, "search_knowledge_base")
        )

        native_system_content = system_content
        if knowledge_search_pending:
            native_system_content = (
                f"{GeneralChatPrompts.KNOWLEDGE_SEARCH_CORRECTION_MSG}\n\n"
                f"{native_system_content}"
            )
        if recall_query_pending:
            native_system_content = (
                f"{MEMORY_SEARCH_CORRECTION_MSG}\n\n"
                f"{native_system_content}"
            )

        if (
            tools
            and all(isinstance(t, RuntimeToolSpec) for t in tools)
        ):
            native_model_handle = await AgentConfigProvider.get_configured_llm(streaming=True, config=self.config)
            native_model = getattr(native_model_handle, "native_model", None)
            if native_model is not None:
                async for chunk in self._execute_with_agentscope_native_agent(
                    native_model=native_model,
                    tools=tools,
                    system_content=native_system_content,
                    runtime_messages=runtime_messages,
                    max_steps=MAX_STEPS,
                ):
                    yield chunk
                return
            yield {
                "type": "error",
                "status": "error",
                "content": "当前模型适配器未提供 AgentScope native_model，无法执行 AgentScope 原生工具链。",
            }
            return

        yield {
            "type": "error",
            "status": "error",
            "content": "GeneralChat 工具链必须使用 AgentScope RuntimeToolSpec；旧 ReAct fallback 已移除。",
        }

    async def _execute_with_agentscope_native_agent(
        self,
        *,
        native_model: Any,
        tools: List[RuntimeToolSpec],
        system_content: str,
        runtime_messages: List[BaseMessage],
        max_steps: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        from agentscope.agent import Agent, ReActConfig

        agent = Agent(
            name=self.config.agent_name or "GeneralAgent",
            system_prompt=system_content,
            model=native_model,
            toolkit=build_toolkit(tools),
            react_config=ReActConfig(max_iters=max_steps),
        )
        inputs = to_agentscope_messages(compat_to_runtime_messages(runtime_messages[1:]))
        state = self._new_agentscope_native_stream_state()
        state["user_query"] = next(
            (
                str(getattr(message, "content", ""))
                for message in reversed(runtime_messages)
                if isinstance(message, HumanMessage)
            ),
            "",
        )
        async for chunk in self._stream_agentscope_native_events(
            event_stream=agent.reply_stream(inputs),
            agent=agent,
            tools=tools,
            native_model=native_model,
            state=state,
        ):
            yield chunk

    def _new_agentscope_native_stream_state(self) -> Dict[str, Any]:
        return {
            "tool_names": {},
            "tool_args_text": {},
            "tool_outputs": {},
            "tool_started_at": {},
            "content_emitted": False,
            "used_tools": False,
            "synthesis_log_emitted": False,
            "full_content": "",
            "start_synthesis": time.time(),
            "synthesis_recorded": False,
        }

    async def _stream_agentscope_native_events(
        self,
        *,
        event_stream: Any,
        agent: Any,
        tools: List[RuntimeToolSpec],
        native_model: Any,
        state: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        tool_names: Dict[str, str] = state["tool_names"]
        tool_args_text: Dict[str, str] = state["tool_args_text"]
        tool_outputs: Dict[str, str] = state["tool_outputs"]
        tool_started_at: Dict[str, float] = state["tool_started_at"]

        async for event in event_stream:
            event_type = str(getattr(event, "type", ""))
            if event_type == "THINKING_BLOCK_DELTA":
                yield {"type": "thinking", "status": "continuing"}
                continue

            if event_type == "TOOL_CALL_START":
                state["used_tools"] = True
                tool_id = getattr(event, "tool_call_id", "")
                tool_name = getattr(event, "tool_call_name", "")
                tool_names[tool_id] = tool_name
                tool_started_at[tool_id] = time.time()
                yield {
                    "type": "log",
                    "id": tool_id,
                    "title": f"调用工具: {tool_name}",
                    "details": "参数: {}",
                    "status": "pending",
                }
                continue

            if event_type == "TOOL_CALL_DELTA":
                tool_id = getattr(event, "tool_call_id", "")
                tool_args_text[tool_id] = tool_args_text.get(tool_id, "") + str(getattr(event, "delta", ""))
                continue

            if event_type == "TOOL_RESULT_TEXT_DELTA":
                tool_id = getattr(event, "tool_call_id", "")
                tool_outputs[tool_id] = tool_outputs.get(tool_id, "") + str(getattr(event, "delta", ""))
                continue

            if event_type == "TOOL_RESULT_END":
                tool_id = getattr(event, "tool_call_id", "")
                tool_name = tool_names.get(tool_id, "")
                raw_args = tool_args_text.get(tool_id, "") or "{}"
                try:
                    tool_args = json.loads(raw_args)
                except Exception:
                    tool_args = {"input": raw_args}
                output = tool_outputs.get(tool_id, "")
                duration_ms = (time.time() - tool_started_at.get(tool_id, time.time())) * 1000
                result = self._build_tool_observation(
                    tool_id=tool_id,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_output=output,
                    duration_tool=duration_ms,
                    target_tool=next((t for t in tools if t.name == tool_name), None),
                    tool_index=0,
                )
                if result.get("log"):
                    yield result["log"]
                if result.get("citation"):
                    yield result["citation"]
                if result.get("trace"):
                    self.trace_buffer.append(result["trace"])
                continue

            if event_type == "REQUIRE_USER_CONFIRM":
                from app.services.ai.runtime.agentscope.confirmations import (
                    pending_agentscope_confirmations,
                )

                for tool_call in getattr(event, "tool_calls", []) or []:
                    tool_id = getattr(tool_call, "id", "") or f"call_{uuid.uuid4().hex[:8]}"
                    tool_name = getattr(tool_call, "name", "")
                    raw_args = getattr(tool_call, "input", "") or "{}"
                    try:
                        tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        tool_args = {"input": raw_args}
                    if not isinstance(tool_args, dict):
                        tool_args = {"input": tool_args}
                    pending = pending_agentscope_confirmations.register(
                        agent=agent,
                        runner=self,
                        tools=tools,
                        native_model=native_model,
                        tool_call=tool_call,
                        reply_id=str(getattr(event, "reply_id", "")),
                        trace_id=self.trace_id,
                        user_id=(self.user_info or {}).get("user_id") or (self.user_info or {}).get("id"),
                        state=state,
                    )
                    yield {
                        "type": "permission_required",
                        "status": "pending",
                        "id": tool_id,
                        "permission_request_id": pending.request_id,
                        "reply_id": pending.reply_id,
                        "expires_in_seconds": 600,
                        "title": f"需要确认工具调用: {tool_name}",
                        "details": f"参数: {json.dumps(tool_args, ensure_ascii=False)}",
                        "tool_call": {
                            "id": tool_id,
                            "name": tool_name,
                            "args": tool_args,
                        },
                    }
                return

            if event_type == "TEXT_BLOCK_DELTA":
                if state["used_tools"] and not state["synthesis_log_emitted"]:
                    state["synthesis_log_emitted"] = True
                    yield {
                        "type": "log",
                        "id": f"synthesis_native_{uuid.uuid4().hex[:8]}",
                        "title": "📝 汇总工具结果",
                        "details": "已获取所需数据，正在组织语言...",
                        "status": "success",
                    }
                    yield {"type": "thinking", "status": "continuing"}
                if not state["content_emitted"]:
                    state["content_emitted"] = True
                    yield {
                        "type": "log",
                        "id": f"gen_start_{uuid.uuid4().hex[:8]}",
                        "title": "✨ 开始生成回复",
                        "status": "success",
                    }
                delta = str(getattr(event, "delta", ""))
                state["full_content"] += delta
                yield {"content": delta}
                continue

            if event_type == "EXCEED_MAX_ITERS":
                yield {"content": GeneralChatPrompts.MAX_STEPS_REACHED}
                return

        if state["full_content"] and not state["synthesis_recorded"]:
            state["synthesis_recorded"] = True
            self._increment_step()
            self.trace_buffer.append(AgentExecutionStep(
                step_number=self.step_counter,
                event_type="synthesis",
                agent_name=self.config.agent_name,
                model=getattr(native_model, "model", self.config.model_name),
                temperature=self.config.synthesis_temperature or self.config.temperature,
                tool_output={"content": state["full_content"]},
                raw_log=state["full_content"],
                execution_time_ms=(time.time() - state["start_synthesis"]) * 1000,
                timestamp=datetime.fromtimestamp(state["start_synthesis"]),
            ))

    async def resume_agentscope_native_confirmation(
        self,
        pending: Any,
        *,
        confirmed: bool,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        from agentscope.event import ConfirmResult, UserConfirmResultEvent

        event = UserConfirmResultEvent(
            reply_id=pending.reply_id,
            confirm_results=[
                ConfirmResult(
                    confirmed=confirmed,
                    tool_call=pending.tool_call,
                )
            ],
        )
        async for chunk in self._stream_agentscope_native_events(
            event_stream=pending.agent.reply_stream(event),
            agent=pending.agent,
            tools=pending.tools,
            native_model=pending.native_model,
            state=pending.state,
        ):
            yield chunk

    def _build_tool_observation(
        self,
        *,
        tool_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_output: Any,
        duration_tool: float,
        target_tool: Any,
        tool_index: int,
    ) -> Dict[str, Any]:
        is_error = "Error" in str(tool_output)

        runtime_cfg = getattr(target_tool, "_runtime_config", None)
        t_model = getattr(runtime_cfg, "model_name", self.config.model_name)
        t_temp = getattr(runtime_cfg, "temperature", self.config.temperature)
        
        # Ensure types for AgentExecutionStep validation (especially when using Mocks in tests)
        if not isinstance(t_model, str): t_model = str(self.config.model_name)
        if not isinstance(t_temp, (int, float)): t_temp = float(self.config.temperature or 0)

        trace_step = AgentExecutionStep(
            step_number=self.step_counter, event_type="tool_call", agent_name=self.config.agent_name,
            model=t_model, temperature=t_temp, tool_name=tool_name, tool_input=tool_args,
            tool_output=tool_output if isinstance(tool_output, (dict, list)) else {"raw": str(tool_output)},
            execution_time_ms=duration_tool, status="success" if not is_error else "error",
            timestamp=datetime.fromtimestamp(time.time() - duration_tool / 1000)
        )
        
        log_event = {"type": "log", "id": tool_id, "title": f"工具完成: {tool_name} ({duration_tool:.0f}ms)", "details": str(tool_output)[:5000], "status": "success" if not is_error else "error", "model": t_model, "temperature": t_temp}
        
        # --- [NEW: Citation Extraction & Multi-Track Unpacking] ---
        citation_event = None
        final_tool_message_content = str(tool_output)

        if tool_name in ["search_knowledge_base", "jira_search"] and not is_error:
            try:
                # 1. Parse JSON Result
                parsed_res = None
                if isinstance(tool_output, str):
                    try:
                        parsed_res = json.loads(tool_output)
                    except:
                        pass
                elif isinstance(tool_output, dict):
                    parsed_res = tool_output

                if isinstance(parsed_res, dict):
                    # Unpack Multi-Track Format
                    # 'content' goes to LLM, 'citations' goes to Frontend
                    if "content" in parsed_res:
                        final_tool_message_content = parsed_res["content"]
                    
                    chunks = parsed_res.get("citations")
                    if isinstance(chunks, list) and len(chunks) > 0:
                        citation_event = {
                            "type": "citation",
                            "tool_call_id": tool_id,
                            "data": chunks
                        }
                elif isinstance(parsed_res, list) and len(parsed_res) > 0:
                    # Backward compatibility for direct array return
                    citation_event = {
                        "type": "citation",
                        "tool_call_id": tool_id,
                        "data": parsed_res
                    }
            except Exception as e:
                logger.warning(f"Failed to extract citations from {tool_name}: {e}")

        return {
            "index": tool_index,
            "final_tool_message_content": final_tool_message_content,
            "trace": trace_step, 
            "log": log_event,
            "citation": citation_event
        }
