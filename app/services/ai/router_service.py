from typing import List, Optional
import json
import logging
from app.core.llm.client import get_llm_async
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RouteResult(BaseModel):
    agent_id: str
    secondary_agents: List[str] = []
    confidence: float
    reasoning: str

class LLMRouterResponse(BaseModel):
    """Internal structure for LLM output."""
    thought: str  # Reasoning/Coreference resolution
    agent_name: str
    secondary_agents: List[str] = []
    confidence: float

class RouterService:

    DEFAULT_SYSTEM_PROMPT = """你是一个智能体平台的智能路由助手。
你的任务是根据用户的输入、智能体描述以及对话上下文，选择最合适的智能体。

### 可用智能体 (Available Agents)
{agents_context}

### 对话历史 (Conversation History)
{history_context}

### 路由推理逻辑 (Reasoning Steps)

1. **指代消解 (Coreference Resolution)**: 
   - 检查用户输入是否包含指代词（如“它”、“这个”、“那里的”、“列表里第一个”）。
   - 结合历史记录，确定这些词具体指向的对象。
   - **示例**: 上文在说“上海机房”，用户问“它有多少服务器？”，应识别出“它”即“上海机房”。

2. **意图领域识别 (Domain Identification)**:
   - **ChatBI (数据专家域)**: 涉及数据库查询、统计、明细、报表、状态监控。
   - **DevOps Expert (运维经验域)**: 涉及故障处理、SOP、工单状态、Jira 任务。
   - **Knowledge Base (非结构化知识)**: 涉及文档、规章制度、SOP流程、定义解释。
   - **General Chat (通用/闲聊)**: 招呼、介绍、感谢、或无法匹配专业领域的请求。

3. **复合意图判定 (Multi-Intent Detection)**:
   - **单一意图**: 用户只询问一个领域的问题。
   - **复合意图**: 用户的问题明确跨越了多个领域（如：既要查数据又要查文档），且这些任务可以并行处理。
   - **处理**: 识别出一个 `agent_name`（主要意图）和若干个 `secondary_agents`。

### 输出格式 (Output Format)
必须返回纯 JSON，严禁包含 Markdown 标记。
{{
  "thought": "在此处写下你的思维过程：1. 消解指代 2. 识别意图领域(是否包含多个) 3. 解释为何选择这些智能体",
  "agent_name": "主要智能体名称",
  "secondary_agents": ["次要智能体名称1", "次要智能体名称2"],
  "confidence": 0.95
}}

### 典型示例 (Examples)
User: "机房 PUE 是什么?"
Output: {{"thought": "用户询问定义，属于知识库范畴。", "agent_name": "knowledge-base", "secondary_agents": [], "confidence": 0.99}}

User: "帮我查下机房负载，顺便看看昨天的异常工单"
Output: {{"thought": "包含数据查询(负载)和工单查询(异常工单)两个意图。", "agent_name": "chat-bi", "secondary_agents": ["devops-expert"], "confidence": 0.96}}"""

    def __init__(self):
        self._agents_cache: List[dict] = []
        self._last_cache_time: float = 0.0
        self._cache_ttl: int = 60 # Seconds

    def invalidate_cache(self):
        """Force clear the agents cache to ensure immediate updates."""
        self._agents_cache = []
        self._last_cache_time = 0.0
        logger.info("RouterService cache invalidated.")

    async def route_query(
        self, 
        user_input: str, 
        history: Optional[List[dict]] = None,
        enable_multi_agent: bool = True,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> Optional[RouteResult]:
        """
        Use LLM to select the most appropriate agent(s) for the user query.
        """
        import time
        from app.services.config_service import ConfigService

        current_time = time.time()
        
        # 1. Fetch Agents (with Caching)
        if self._agents_cache and (current_time - self._last_cache_time < self._cache_ttl):
            agents_metadata = self._agents_cache
        else:
            agents_metadata = await self._fetch_agents_from_db()
            if agents_metadata:
                self._agents_cache = agents_metadata
                self._last_cache_time = current_time
        
        if not agents_metadata:
            logger.warning("No agents available for routing.")
            return None

        agents_metadata = await self._filter_agents_for_user(
            agents_metadata,
            user_id=user_id,
            is_admin=is_admin,
        )
        if not agents_metadata:
            logger.warning("No routeable agents available for user %s.", user_id)
            return None

        # 2. Unified LLM Routing
        system_prompt = await ConfigService.get("router_system_prompt", self.DEFAULT_SYSTEM_PROMPT)
        agents_str = self._build_agents_context(agents_metadata)
        
        history_str = ""
        if history:
            history_str = "Conversation History (recent rounds):\n"
            recent_history = history[-6:] if len(history) > 6 else history
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role != "system":
                    history_str += f"- {role.capitalize()}: {content}\n"
            history_str += "\nAnalyze the user's latest query in the context of this conversation."
        
        formatted_prompt = system_prompt.replace("{agents_context}", agents_str).replace("{history_context}", history_str)
        
        try:
            llm = await get_llm_async(temperature=0.0) # Use deterministic output
            messages = [
                SystemMessage(content=formatted_prompt),
                HumanMessage(content=f"Latest User Query: {user_input}")
            ]
            
            response = await llm.ainvoke(messages)
            content = response.content.strip()
            
            # Remove potential markdown code blocks
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    content = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
            content = content.strip()
            
            logger.info(f"LLM Routing Response: {content}")
            
            try:
                result_json = json.loads(content)
            except json.JSONDecodeError:
                # Fallback for very simple cleaning if LLM adds text before/after JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                else:
                    raise

            confidence = result_json.get('confidence', 0.5)
            target_name = result_json.get("agent_name")
            secondary_names = result_json.get("secondary_agents", [])
            reasoning = result_json.get("thought") or result_json.get("reasoning", "")
            
            # --- Confidence & Fallback Mechanism ---
            if confidence < 0.6:
                logger.info(f"Low confidence ({confidence}) for '{target_name}'. Falling back to General Chat.")
                return self._fallback_to_general(agents_metadata, f"Low confidence ({confidence}) for agent selection. Reason: {reasoning}")

            # Resolve primary name back to ID
            target_agent = next((a for a in agents_metadata if a['name'].lower() == str(target_name).lower()), None)
            
            if target_agent:
                # Resolve secondary names back to IDs if multi-agent is enabled
                resolved_secondaries = []
                if enable_multi_agent and secondary_names:
                    for s_name in secondary_names:
                        s_agent = next((a for a in agents_metadata if a['name'].lower() == str(s_name).lower()), None)
                        if s_agent and s_agent['id'] != target_agent['id']:
                            resolved_secondaries.append(s_agent['id'])

                return RouteResult(
                    agent_id=target_agent['id'],
                    secondary_agents=resolved_secondaries,
                    confidence=confidence,
                    reasoning=reasoning
                )
            else:
                logger.warning(f"Router suggested unknown agent: {target_name}. Falling back to General Chat.")
                return self._fallback_to_general(agents_metadata, f"Router returned unknown agent: {target_name}")
                
        except Exception as e:
            logger.error(f"Routing failed: {e}. Falling back to General Chat.")
            return self._fallback_to_general(agents_metadata, f"Routing exception ({str(e)})")

    async def _fetch_agents_from_db(self) -> List[dict]:
        from app.core.orm import AsyncSessionLocal
        from app.models.agent import AIAgent
        from sqlalchemy import select
        
        agents_metadata = []
        async with AsyncSessionLocal() as session:
            # Only select enabled agents AND system agents for routing
            result = await session.execute(
                select(AIAgent).where(AIAgent.is_enabled == True, AIAgent.is_system == True)
            )
            agents = result.scalars().all()
            for agent in agents:
                agents_metadata.append({
                    "id": agent.id,
                    "name": agent.name,
                    "display_name": agent.display_name or agent.name,  # 中文显示名，用于路由匹配兜底
                    "description": agent.description or "No description provided.",
                    "capabilities": agent.capabilities or []
                })
        return agents_metadata

    async def _filter_agents_for_user(
        self,
        agents: List[dict],
        *,
        user_id: Optional[int],
        is_admin: bool = False,
    ) -> List[dict]:
        if is_admin or not user_id:
            return agents

        try:
            from app.core.orm import AsyncSessionLocal
            from app.services.permission_service import PermissionService

            async with AsyncSessionLocal() as session:
                perms = await PermissionService(session).get_user_permissions(int(user_id))
                if "admin" in getattr(perms, "roles", []):
                    return agents
                allowed_agent_ids = set(getattr(perms.permissions, "agents", []) or [])
        except Exception as e:
            logger.warning("Failed to filter route agents for user %s: %s", user_id, e)
            return agents

        return [agent for agent in agents if agent.get("id") in allowed_agent_ids]

    def _build_agents_context(self, agents: List[dict]) -> str:
        agents_str = ""
        for agent in agents:
            display = agent.get("display_name", "")
            # 若有独立的中文显示名，在 Prompt 里一并提供，让 LLM 能用中文名路由
            name_info = f"{agent['name']}"
            if display and display != agent["name"]:
                name_info += f" (中文名: {display})"
            agents_str += f"- ID: {name_info} (UUID: {agent['id']})\n"
            agents_str += f"  Description: {agent['description']}\n"
            agents_str += f"  Capabilities: {agent['capabilities']}\n\n"
        return agents_str

    def _fallback_to_general(self, agents: List[dict], reason: str) -> Optional[RouteResult]:
        fallback_agent = next((a for a in agents if a['name'] == 'general-chat'), None)
        if fallback_agent:
            return RouteResult(
                agent_id=fallback_agent['id'],
                confidence=0.1,
                reasoning=f"Fallback: {reason}"
            )
        return None

router_service = RouterService()
