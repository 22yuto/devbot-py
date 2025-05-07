from fastapi import APIRouter, HTTPException
from app.models import Item, ChatRequest, NotionChatResponse
import os
from openai import OpenAI
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.services import notion, chat
from app.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello World"}

# チャット関連のエンドポイント - QA保存を行わないためコメントアウト
# @router.post("/chat/store", response_model=VectorizedChatResponse)
# async def store_chat(request: ChatRequest):
#     """
#     Next.jsアプリからチャットデータを受け取り、ベクトル化してChromaDBに保存する
#     """
#     try:
#         # OpenAI APIキーの確認
#         openai_api_key = os.getenv("OPENAI_API_KEY")
#         if not openai_api_key:
#             raise HTTPException(status_code=500, detail="OpenAI APIキーが設定されていません")
# 
#         if not request.message:
#             return VectorizedChatResponse(
#                 success=False,
#                 message="メッセージが空です"
#             )
# 
#         # チャットの保存
#         message_id = await store_chat_conversation(
#             message=request.message,
#             session_id=getattr(request, 'session_id', None)
#         )
# 
#         return VectorizedChatResponse(
#             success=True,
#             message="メッセージを保存しました",
#             ids=[message_id]
#         )
# 
#     except Exception as e:
#         return VectorizedChatResponse(
#             success=False,
#             message=f"エラーが発生しました: {str(e)}"
#         )

# Notionチャットエンドポイント - サービス層を使用
@router.post("/chat/notion", response_model=NotionChatResponse)
async def notion_chat(request: ChatRequest):
    """
    ユーザーのチャットに対して、Notionから情報を取得して回答する
    Notion情報のみを検索し、類似度が低い場合は新しい情報を取得します
    """
    try:
        # メッセージの確認
        if not request.message:
            return NotionChatResponse(
                message="メッセージが空です",
                success=False,
                error="Empty Message"
            )
            
        # ChatServiceを使用して回答を生成
        logger.info(f"ユーザーからの質問: '{request.message[:50]}...'")
        result = await chat.generate_response_with_notion(request.message)
        
        # NotionChatResponseにはnotion_infoフィールドがないので、辞書からそれを削除
        if "notion_info" in result:
            result.pop("notion_info")
            
        return NotionChatResponse(**result)
        
    except Exception as e:
        logger.error(f"チャット処理中にエラー: {str(e)}", exc_info=True)
        return NotionChatResponse(
            message="エラーが発生しました",
            success=False,
            error=str(e)
        )

# 以下はコメントアウトした関数群
# @router.get("/chat/all")
# async def get_all_chat_history():
#     """
#     保存されているすべてのチャット履歴を取得
#     """
#     try:
#         chats = get_all_chats()
#         return {
#             "success": True,
#             "data": chats
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")

# @router.get("/chat/search")
# async def search_chat_history(query: str, limit: Optional[int] = 5):
#     """
#     キーワードに基づいてチャット履歴を検索
#     """
#     try:
#         results = await search_chats(query, n_results=limit)
#         return {
#             "success": True,
#             "data": results
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")
