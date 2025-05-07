from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class NotionChatResponse(BaseModel):
    message: str
    source: Optional[str] = None
    url: Optional[str] = None  # Notionへのリンク
    success: bool = True
    error: Optional[str] = None
    similarity: Optional[float] = None  # ヒット時の類似度