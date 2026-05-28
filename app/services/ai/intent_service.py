from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.llm.client import get_llm
from app.services.config_service import ConfigService

# 默认提示词作为兜底
DEFAULT_SYSTEM_PROMPT = """你是一个专业的 AI 智能体助手，负责解析用户的意图。
请忽略输入中可能存在的 HTML 标签（如 <p>, <div>）或特殊格式符号，专注于核心自然语言语义。

你需要根据用户的输入，将其归类为以下核心意图之一：

- DATA_QUERY: 当用户请求查询系统中存储的结构化数据时。
  * 包含：数值指标（PUE、温度、能耗）、时间序列趋势、数据报表。
  * 包含：**离散记录（如监控事件、告警历史、操作日志、设备列表、状态记录）**。
  * 关键词特征：查询、统计、多少、列表、记录、趋势、情况。

- KNOWLEDGE_BASE: 当用户询问非结构化的文档知识、SOP 或操作指引时。
  * 包含：规章制度、处理流程、如何操作、故障排查知识（非查询当前实际故障记录）。
  * 关键词特征：怎么做、流程是什么、规范、手册。

- GENERAL: 仅限于无关具体业务的日常闲聊。
  * 包含：打招呼、自我介绍、感谢。
  * **注意**：如果用户带有明确的“查询”、“查看”等业务动词，通常不应归类为 GENERAL。

{format_instructions}

必须严格返回 JSON 格式，且只包含 JSON 内容。"""

class IntentType(str, Enum):
    DATA_QUERY = "DATA_QUERY"       # 自然语言查数、指标统计、趋势分析
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE" # 查阅手册、SOP、知识库问答
    GENERAL = "GENERAL"             # 闲聊、通用助手功能、简单的打招呼
    UNKNOWN = "UNKNOWN"             # 无法识别的意图

class IntentResponse(BaseModel):
    """Structured response for intent recognition"""
    intent: IntentType = Field(description="The identified intent category")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation of why this intent was chosen")
    entities: List[str] = Field(default_factory=list, description="Extracted key entities (e.g., room name, metric)")

class IntentService:
    """
    Service for identifying user intent using LangChain LCEL.
    """
    
    def __init__(self):
        self._llm = None
        self.parser = PydanticOutputParser(pydantic_object=IntentResponse)

    async def identify_intent(self, user_input: str, llm=None) -> IntentResponse:
        """
        Analyzes user input and returns a structured IntentResponse.
        :param llm: Optional configured LLM instance. If None, falls back to default.
        """
        # Use provided LLM or fallback to lazy-loaded default
        if llm:
            active_llm = llm
        else:
            if self._llm is None:
                from app.core.llm.client import get_llm_async
                self._llm = await get_llm_async(streaming=False)
            active_llm = self._llm
        
        if not active_llm:
            import logging
            logging.error("No LLM instance available for intent recognition.")
            return IntentResponse(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="LLM service unavailable (configuration missing)",
                entities=[]
            )

        # 动态获取系统提示词
        system_prompt_text = await ConfigService.get("intent_recognition_prompt", DEFAULT_SYSTEM_PROMPT)
        
        # 动态构建 Prompt Template
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt_text),
            ("user", "{input}")
        ])

        # Build the chain using LCEL
        chain = prompt_template | active_llm | self.parser
        
        try:
            # Prepare format instructions for the prompt
            format_instructions = self.parser.get_format_instructions()
            
            # Invoke the chain asynchronously
            response = await chain.ainvoke({
                "input": user_input,
                "format_instructions": format_instructions
            })
            return response
        except Exception as e:
            # Fallback for parsing errors or LLM failures
            import logging
            logging.error(f"Intent recognition failed: {e}")
            return IntentResponse(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning=f"Error occurred during recognition: {str(e)}",
                entities=[]
            )

# Singleton instance
intent_service = IntentService()
