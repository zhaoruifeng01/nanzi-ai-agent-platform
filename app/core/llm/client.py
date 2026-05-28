from typing import Optional
from langchain_openai import ChatOpenAI
from app.core.config import settings

class LLMFactory:
    """
    Factory for creating LangChain Chat Model instances.
    Centralizes LLM configuration and allows for easy provider switching.
    """
    
    @staticmethod
    def get_chat_model(
        streaming: bool = False,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: float = None
    ) -> ChatOpenAI:
        """
        Returns a configured ChatOpenAI instance compatible with OpenAI protocol.
        Allows runtime overrides for dynamic configuration.
        """
        # Validate key presence if needed, or let ChatOpenAI handle it.
        # Ensure we don't rely on settings if they are None.
        
        final_api_key = api_key or (settings.LLM_API_KEY if settings.LLM_API_KEY else None)
        final_base_url = base_url or (settings.LLM_BASE_URL if settings.LLM_BASE_URL else None)
        final_model = model or (settings.LLM_MODEL_NAME if settings.LLM_MODEL_NAME else "default-model")
        final_temp = temperature if temperature is not None else (settings.LLM_TEMPERATURE if settings.LLM_TEMPERATURE is not None else 0.7)

        import logging
        masked_key = final_api_key[:8] + "***" if final_api_key else "None"
        logging.error(f"Creating ChatOpenAI with Key: {masked_key}, BaseURL: {final_base_url}, Model: {final_model}")

        return ChatOpenAI(
            openai_api_key=final_api_key,
            openai_api_base=final_base_url,
            model_name=final_model,
            temperature=final_temp,
            streaming=streaming,
            max_retries=3,
        )

# Global helper to get the default model
def get_llm(streaming: bool = False, **kwargs) -> ChatOpenAI:
    return LLMFactory.get_chat_model(streaming=streaming, **kwargs)

async def get_llm_async(streaming: bool = False, **kwargs) -> Optional[ChatOpenAI]:
    """
    Asynchronously creates an LLM instance.
    Prioritizes:
    1. kwargs overrides
    2. ai_models table lookup (if model name matches)
    3. Legacy system_configs/Env (fallback)
    """
    from app.services.config_service import ConfigService
    
    # 1. Determine the target model name
    db_model_name = await ConfigService.get("llm_model_name")
    model = kwargs.get("model") or db_model_name or settings.LLM_MODEL_NAME or "default-model"
    
    # 2. Try looking up in Model Management Registry
    api_key = kwargs.get("api_key")
    base_url = kwargs.get("base_url")
    
    try:
        from app.core.orm import AsyncSessionLocal
        from app.models.ai_model import AIModel
        from sqlalchemy import select, or_
        
        async with AsyncSessionLocal() as session:
            stmt = select(AIModel).where(
                AIModel.is_active == True,
                or_(AIModel.model_id == model, AIModel.name == model)
            )
            result = await session.execute(stmt)
            ai_model = result.scalars().first()
            
            if ai_model:
                # Found registered model, use its credentials if not provided in kwargs
                api_key = api_key or ai_model.api_key
                base_url = base_url or ai_model.api_base_url
                # Use the actual model_id for the provider
                model = ai_model.model_id
    except Exception as e:
        import logging
        logging.warning(f"Model registry lookup failed in get_llm_async: {e}")

    # 3. Final Fallback to Legacy/Env
    if not api_key:
        api_key = await ConfigService.get("llm_api_key") or settings.LLM_API_KEY
    if not base_url:
        base_url = await ConfigService.get("llm_base_url") or settings.LLM_BASE_URL
        
    db_temp = await ConfigService.get("llm_temperature")
    try:
        temperature = float(kwargs.get("temperature") or db_temp or settings.LLM_TEMPERATURE or 0.7)
    except (TypeError, ValueError):
        temperature = 0.7

    if not api_key:
        import logging
        logging.error(f"LLM API Key is missing for model '{model}'. Cannot create LLM instance.")
        return None

    import logging
    masked_key = api_key[:8] + "***" if api_key else "None"
    logging.info(f"Async creating ChatOpenAI: Model={model}, BaseURL={base_url}, Key={masked_key}")

    return ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base=base_url,
        model_name=model,
        temperature=temperature,
        streaming=streaming,
        max_retries=3,
    )
