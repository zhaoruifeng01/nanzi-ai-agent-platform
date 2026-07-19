import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_api_key
from app.core.orm import get_db_session
from app.models.chatbi_analysis import ChatBIBrief
from app.schemas.response import StandardResponse
from app.services.ai.chatbi_result_stack import ChatBIResultRef, resolve_result_reference
from app.services.ai.memory_service import memory_service
from app.services.chatbi_brief_service import build_business_brief, publish_business_brief_docx

router = APIRouter()


class CreateChatBIBriefRequest(BaseModel):
    conversation_id: str
    result_id: Optional[str] = None
    export_word: bool = True


@router.post("", summary="从当前 ChatBI 结果一键生成业务简报")
async def create_chatbi_brief(
    body: CreateChatBIBriefRequest,
    user_info=Depends(require_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    user_id = str(user_info["user_id"])
    stack = await memory_service.get_data_result_stack(user_id, body.conversation_id)
    if not stack:
        legacy = await memory_service.get_current_data_result(user_id, body.conversation_id)
        stack = [legacy] if legacy else []
    refs = [ChatBIResultRef.from_dict(item) for item in stack if isinstance(item, dict)]
    reference = resolve_result_reference(
        refs,
        body.result_id or "当前结果",
    )
    if reference.result is None:
        detail = "结果引用不明确" if reference.candidates else "当前会话没有可生成简报的结构化结果"
        raise HTTPException(status_code=409, detail=detail)
    result_payload = reference.result.to_dict()
    brief = build_business_brief(result_payload)
    artifact_payload = None
    if body.export_word:
        artifact_payload = publish_business_brief_docx(brief).to_tool_payload()
    brief_id = f"brief_{uuid.uuid4().hex}"
    row = ChatBIBrief(
        id=brief_id,
        owner_user_id=int(user_id),
        conversation_id=body.conversation_id,
        result_id=reference.result.result_id,
        title=brief["title"],
        brief_payload={key: value for key, value in brief.items() if key != "markdown"},
        markdown_content=brief["markdown"],
        artifact_payload=artifact_payload,
    )
    db.add(row)
    await db.flush()
    return StandardResponse(data={
        "id": brief_id,
        **brief,
        "artifact": artifact_payload,
    })
