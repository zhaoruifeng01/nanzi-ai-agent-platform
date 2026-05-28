import logging
import json
import time
from typing import List, Dict, Any, Optional
from app.schemas.agent import AgentExecutionStep, ChatConfig
from app.services.ai.intent_service import intent_service, IntentType
from app.services.ai.executors.base import BaseExecutor
from app.services.ai.executors.data_executor import DataQueryExecutor
from app.services.ai.executors.chat_executor import GeneralChatExecutor
from app.services.ai.executors.rag_executor import RAGExecutor
from app.services.ai.executors.openclaw_executor import OpenClawExecutor

logger = logging.getLogger(__name__)

class AgentDispatcher:
    """
    Dispatches agent execution to the appropriate Executor based on configuration and intent.
    """

    @staticmethod
    async def dispatch(
        agent_config: ChatConfig,
        user_query: str,
        messages: List[Dict[str, str]],
        trace_id: str,
        trace_buffer: List[AgentExecutionStep],
        debug_options: Optional[Dict[str, Any]] = None,
        user_info: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> BaseExecutor:
        """
        Determines and returns the correct Executor instance.
        """
        
        # 1. External Engine Check
        if agent_config.engine_type == 'RAGFLOW':
            return RAGExecutor(agent_config, trace_id, trace_buffer, debug_options, user_info, conversation_id)
        
        if agent_config.engine_type == 'OPENCLAW':
            return OpenClawExecutor(agent_config, trace_id, trace_buffer, debug_options, user_info, conversation_id)

        # 2. Standard Intent Recognition
        intent_start = time.time()
        intent_info = await intent_service.identify_intent(user_query)
        intent_elapsed_ms = (time.time() - intent_start) * 1000
        
        # 3. Capability Check
        can_do_data = "data_query" in (agent_config.capabilities or [])
        
        if intent_info.intent == IntentType.DATA_QUERY and can_do_data:
            executor = DataQueryExecutor(agent_config, trace_id, trace_buffer, debug_options, user_info, conversation_id)
            executor.intent_info = intent_info # Attach for potential use
            executor.intent_elapsed_ms = intent_elapsed_ms
            return executor
        else:
             # Fallback to General Chat
             return GeneralChatExecutor(agent_config, trace_id, trace_buffer, debug_options, user_info, conversation_id)
