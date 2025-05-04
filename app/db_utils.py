import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import openai
from chromadb import HttpClient
from app.models import ChatMessage

# ChromaDBクライアントの初期化 - 永続化モード
client = HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("chat_history")
collection_name = "chat_history"

# コレクションが存在しない場合は作成
try:
    collection = client.get_collection(collection_name)
    print(f"既存のコレクション '{collection_name}' を使用します")
except Exception as e:
    print(f"新しいコレクション '{collection_name}' を作成します: {str(e)}")
    collection = client.create_collection(collection_name)

async def get_embeddings(text: str) -> List[float]:
    """
    OpenAIのAPIを使用してテキストのエンベディングを取得
    """
    response = await openai.Embedding.acreate(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def store_chat_message(message: ChatMessage, session_id: Optional[str] = None) -> str:
    """
    チャットメッセージをベクトル化してChromaDBに保存
    """
    # メッセージIDの生成
    message_id = str(uuid.uuid4())

    # メタデータの準備
    metadata = message.metadata or {}
    metadata.update({
        "role": message.role,
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id or "unknown_session"
    })

    # テキストのエンベディングを取得
    embedding = await get_embeddings(message.content)

    # ChromaDBに保存
    collection.add(
        ids=[message_id],
        embeddings=[embedding],
        documents=[message.content],
        metadatas=[metadata]
    )

    return message_id

async def store_chat_conversation(messages: List[ChatMessage], session_id: Optional[str] = None) -> List[str]:
    """
    会話全体を保存し、生成されたIDのリストを返す
    """
    message_ids = []

    for message in messages:
        message_id = await store_chat_message(message, session_id)
        message_ids.append(message_id)

    return message_ids

def get_all_chats():
    """
    保存されているすべてのチャットデータを取得
    """
    return collection.get()

async def search_chats(query: str, n_results: int = 5):
    """
    クエリに関連するチャットを検索
    """
    embedding = await get_embeddings(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )
    return results
