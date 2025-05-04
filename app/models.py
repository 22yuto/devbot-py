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
    messages: List[ChatMessage]
    session_id: Optional[str] = None  # セッションID（オプション）

class VectorizedChatResponse(BaseModel):
    success: bool
    message: str
    ids: List[str] = []
