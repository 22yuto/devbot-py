from fastapi import APIRouter
from app.models import ChatRequest, NotionChatResponse
from openai import OpenAI
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.services import notion, chat

router = APIRouter()

"""
Notionから情報を取得して回答
"""
@router.post("/chat/notion", response_model=NotionChatResponse)
async def notion_chat(request: ChatRequest):
    try:
        if not request.message:
            return NotionChatResponse(
                message="どうしましたか？何か質問があれば仰ってください。",
                success=False,
                error="Empty Message"
            )

        # 回答を生成
        result = await chat.generate_response_with_notion(request.message)
        return NotionChatResponse(**result)

    except Exception as e:
        return NotionChatResponse(
            message="エラーが発生しました",
            success=False,
            error=str(e)
        )