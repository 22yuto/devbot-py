import uuid
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI
from chromadb import HttpClient
from app.models import ChatMessage
from dotenv import load_dotenv, find_dotenv
from app.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    print(".env ファイルがありません")

# OpenAIクライアントの初期化（環境変数から直接取得）
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

# ChromaDBクライアントの初期化 - 永続化モード
client = HttpClient(host="localhost", port=8100)

# 設定値を環境変数から取得
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
DEFAULT_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

async def get_embeddings(text: str) -> List[float]:
    """
    OpenAIのAPIを使用してテキストのエンベディングを取得（新しいAPI方式）
    """
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


async def store_notion_info(user_query: str, notion_info: Dict, session_id: Optional[str] = None) -> str:
    """
    ユーザーの質問とそれに対応するNotion情報のみを保存します。
    チャンク分割して保存するようになりました。
    
    Args:
        user_query: ユーザーからの質問
        notion_info: Notionから取得した情報
        session_id: セッションID（オプション）
    
    Returns:
        生成された最初のチャンクID
    """
    chunk_ids = await store_notion_chunks(user_query, notion_info, session_id)
    return chunk_ids[0] if chunk_ids else str(uuid.uuid4())

async def find_similar_notion_info(user_query: str, threshold: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    類似したクエリに使用されたNotion情報を検索します。
    チャンク分割されたNotion情報に対応しています。
    閾値による切り捨てではなく、Top-Nの中から最もスコアが高いものを採用します。
    
    Args:
        user_query: ユーザーからの質問
        threshold: 類似度の閾値 (Noneの場合はデフォルト値を使用)
    
    Returns:
        最も類似度が高いNotion情報
    """
    similarity_threshold = threshold if threshold is not None else SIMILARITY_THRESHOLD
    
    try:
        # Notionコレクションを取得
        notion_collection = client.get_or_create_collection("notion_info")
        logger.info(f"Notionコレクション取得: {notion_collection.name}, コレクションサイズ: {len(notion_collection.get().get('ids', []))}件")
        
        # 検索結果の最大件数
        n_results = 20
        
        # ユーザークエリから直接クエリを実行
        query_embedding = await get_embeddings(user_query)
        
        # 類似したチャンクを検索
        logger.info(f"Notionコレクションから類似チャンクを検索中... (Top-{n_results})")
        results = notion_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            logger.info("Notionコレクションに項目が見つかりません")
            return None
            
        # 検索結果の距離（類似度）から類似度を計算
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        if not distances or not metadatas:
            logger.info("検索結果が空です")
            return None
        
        # ページIDごとにチャンクをグループ化
        page_chunks = {}
        page_best_similarity = {}
        
        # 検索結果のログ出力（デバッグ用）
        logger.debug(f"検索結果: {len(distances)}件")
        for i in range(min(5, len(distances))):
            similarity = 1.0 - distances[i]
            logger.info(f"  検索結果 {i+1}: 類似度={similarity:.3f}, タイトル='{metadatas[i].get('notion_title', '')[:30]}...'")
        
        for i, (distance, metadata) in enumerate(zip(distances, metadatas)):
            # 類似度を計算（距離を類似度に変換）
            similarity = 1.0 - distance
            
            # 参考のため閾値との比較をログに出力（ただし切り捨てはしない）
            if similarity < similarity_threshold:
                logger.debug(f"類似度が閾値より低い項目: {similarity:.3f} < {similarity_threshold:.3f}")
            
            page_id = metadata.get("notion_page_id", "")
            if not page_id:
                logger.debug("ページIDがないためスキップ")
                continue  # ページIDがない場合はスキップ
            
            # ページごとに最高の類似度を記録
            if page_id not in page_best_similarity or similarity > page_best_similarity[page_id]:
                page_best_similarity[page_id] = similarity
            
            # ページIDでチャンクをグループ化
            if page_id not in page_chunks:
                page_chunks[page_id] = []
            
            # チャンク情報を保存
            chunk_info = {
                "chunk_index": metadata.get("chunk_index", 0),
                "content": metadata.get("notion_content_chunk", ""),
                "title": metadata.get("notion_title", ""),
                "url": metadata.get("notion_url", ""),
                "similarity": similarity,
                "query": metadata.get("query", "")
            }
            page_chunks[page_id].append(chunk_info)
        
        # ページがない場合
        if not page_chunks:
            logger.info("有効なページが見つかりませんでした")
            return None
        
        # 最も類似度の高いページを特定
        best_page_id = max(page_best_similarity, key=page_best_similarity.get)
        best_similarity = page_best_similarity[best_page_id]
        
        logger.info(f"最適なページ {best_page_id} を選択 (類似度: {best_similarity:.2f}, チャンク数: {len(page_chunks[best_page_id])})")
        
        # 最適なページのチャンクを順序付けて結合
        chunks = sorted(page_chunks[best_page_id], key=lambda x: x["chunk_index"])
        
        # ページ情報を構築
        if chunks:
            # 最初のチャンクからメタデータを取得
            first_chunk = chunks[0]
            
            # すべてのチャンクコンテンツを結合
            combined_content = "\n".join([chunk["content"] for chunk in chunks])
            
            notion_info = {
                "title": first_chunk["title"],
                "page_id": best_page_id,
                "url": first_chunk["url"],
                "content": combined_content
            }
            
            result = {
                "notion_info": notion_info,
                "similarity": best_similarity,
                "original_query": first_chunk["query"]
            }
            
            logger.info(f"チャンクを結合して完全なコンテンツを作成しました (合計 {len(combined_content)} 文字)")
            return result
        
        return None
        
    except Exception as e:
        logger.error(f"Notion情報検索中にエラー: {str(e)}", exc_info=True)
        return None

async def get_collection_info(collection_name: str = "notion_info") -> Dict[str, Any]:
    """
    指定されたコレクションの情報を取得します。
    
    Args:
        collection_name: コレクション名
        
    Returns:
        コレクション情報を含む辞書: {"exists": bool, "size": int, "collection": Collection}
    """
    try:
        collection = client.get_or_create_collection(collection_name)
        collection_data = collection.get()
        
        ids = collection_data.get("ids", [])
        size = len(ids)
        
        return {
            "exists": True,
            "size": size,
            "has_data": size > 0,
            "collection": collection
        }
        
    except Exception as e:
        logger.error(f"コレクション情報取得中にエラー: {str(e)}", exc_info=True)
        return {
            "exists": False,
            "size": 0,
            "has_data": False,
            "collection": None
        }
