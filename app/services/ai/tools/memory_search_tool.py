"""Tool: search cross-session memory (summaries + optional history)."""
import json
import logging
from typing import Optional

from langchain_core.tools import tool

from app.core.context import get_current_agent_context
from app.services.ai.session_summary_service import SessionSummaryService
from app.services.memory_config_service import MemoryConfigService

logger = logging.getLogger(__name__)


@tool
async def memory_search(
    scope: str = "summary",
    query: Optional[str] = None,
    conversation_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """检索当前用户跨会话历史：摘要列表或指定会话消息明细。当用户问「今天我们聊了啥」「最近/上次聊了什么」「有没有讨论过」「回顾历史对话」时必须优先调用；新会话 messages 为空不代表从未聊过。禁止未调用本工具就声称「第一次对话」或编造历史。scope=summary 查跨会话摘要（有 query 则语义检索）；scope=history 需 conversation_id 拉该会话 Redis 明细；scope=both 先摘要再明细。user_id 由系统自动隔离，勿传入他人 ID。

    Args:
        scope: summary | history | both
        query: 检索关键词或自然语言问句（如「今天」「机房」），用于摘要语义/关键词匹配
        conversation_id: history/both 时目标会话 ID
        limit: 返回条数上限
    """
    if not await MemoryConfigService.get_bool("memory_service_enabled", True):
        return "记忆服务未启用，无法检索历史会话。"

    ctx = get_current_agent_context()
    if not ctx or not ctx.user_id:
        return "无法识别当前用户，拒绝检索记忆。"

    top_k = limit if limit is not None else await MemoryConfigService.get_int("memory_search_knn_top_k", 5)
    scope_norm = (scope or "summary").strip().lower()
    if scope_norm not in ("summary", "history", "both"):
        scope_norm = "summary"

    try:
        data = await SessionSummaryService.search_for_user(
            user_id=str(ctx.user_id),
            query=query,
            scope=scope_norm,
            conversation_id=conversation_id,
            limit=top_k,
        )
    except Exception as e:
        logger.error("[memory_search] failed: %s", e)
        return f"记忆检索失败: {e}"

    lines = []
    summaries = data.get("summaries") or []
    if summaries:
        lines.append("## 匹配的会话摘要\n")
        for i, s in enumerate(summaries, 1):
            score = s.get("score")
            score_txt = f" (相关度: {score:.3f})" if score is not None else ""
            lines.append(
                f"{i}. **{s.get('title', '未命名')}**{score_txt}\n"
                f"   - conversation_id: `{s.get('conversation_id')}`\n"
                f"   - 最后活跃: {s.get('last_active')}\n"
                f"   - 摘要: {s.get('summary', '')}\n"
            )
    else:
        lines.append("未找到匹配的会话摘要。")

    history = data.get("history") or []
    if history:
        cid = data.get("conversation_id") or conversation_id
        lines.append(f"\n## 会话明细 ({cid})\n")
        for m in history:
            role = m.get("role", "?")
            content = (m.get("content") or "")[:1500]
            lines.append(f"- **{role}**: {content}\n")

    return "\n".join(lines) if lines else "无记忆数据。"
