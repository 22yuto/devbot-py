from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Item(BaseModel):
    id: int
    name: str

class ChatMessage(BaseModel):
    content: str
    role: str = "user"  # デフォルトはユーザーからのメッセージ
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class VectorizedChatResponse(BaseModel):
    success: bool
    message: str
    ids: List[str] = []

# レスポンスモデル
class NotionChatResponse(BaseModel):
    message: str
    source: Optional[str] = None
    url: Optional[str] = None  # Notionページへのリンク
    success: bool = True
    error: Optional[str] = None
    from_cache: bool = False  # キャッシュからの回答かどうか
    similarity: Optional[float] = None  # キャッシュヒット時の類似度