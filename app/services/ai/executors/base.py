from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional
from app.schemas.agent import ChatConfig, AgentExecutionStep

class BaseExecutor(ABC):
    """
    Base class for all Agent Executors.
    Defines the contract for streaming execution.
    """
    
    def __init__(
        self, 
        config: ChatConfig, 
        trace_id: str, 
        trace_buffer: List[AgentExecutionStep],
        debug_options: Dict[str, Any] = None,
        user_info: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ):
        self.config = config
        self.trace_id = trace_id
        self.trace_buffer = trace_buffer
        self.debug_options = debug_options or {}
        self.user_info = user_info
        self.conversation_id = conversation_id
        self.step_counter = 0

    @abstractmethod
    async def execute(
        self, 
        history: List[Dict[str, str]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main execution loop. Must yield dicts compatible with SSE.
        """
        pass

    def _increment_step(self) -> int:
        self.step_counter += 1
        return self.step_counter
