from fastapi import APIRouter, HTTPException
from app.models import Item, ChatRequest, VectorizedChatResponse
import os
import openai
from app.db_utils import store_chat_conversation, get_all_chats, search_chats
from typing import Optional

# OpenAI APIキーの設定
# 注: 実際の実装では環境変数から取得するか、セキュアな方法で管理してください
openai.api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello World"}
@router.post("/test")
async def test():
    return {"message": "test"}

@router.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int, q: str | None = None):
    return {"id": item_id, "name": f"Item {item_id}"}

# チャット関連のエンドポイント
@router.post("/chat/store", response_model=VectorizedChatResponse)
async def store_chat(request: ChatRequest):
    """
    Next.jsアプリからチャットデータを受け取り、ベクトル化してChromaDBに保存する
    """
    try:
        # OpenAI APIキーの確認
        if not openai.api_key:
            raise HTTPException(status_code=500, detail="OpenAI APIキーが設定されていません")

        if not request.messages:
            return VectorizedChatResponse(
                success=False,
                message="メッセージが空です"
            )

        # チャットの保存
        message_ids = await store_chat_conversation(
            messages=request.messages,
            session_id=request.session_id
        )

        return VectorizedChatResponse(
            success=True,
            message=f"{len(message_ids)}件のメッセージを保存しました",
            ids=message_ids
        )

    except Exception as e:
        return VectorizedChatResponse(
            success=False,
            message=f"エラーが発生しました: {str(e)}"
        )

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
