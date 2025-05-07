import uuid
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from chromadb import HttpClient
from chromadb.api.models.Collection import Collection
from dotenv import load_dotenv, find_dotenv
from app.logger import get_logger
from app.utils.openai import get_embeddings

logger = get_logger(__name__)

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    print(".env ファイルがありません")

# ChromaDBクライアントの初期化 - 永続化モード
client = HttpClient(host="localhost", port=8100)

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
DEFAULT_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

"""
ユーザーの質問とそれに対応するNotion情報のみを保存
"""
async def store_notion_info(user_query: str, notion_info: Dict) -> str:
    chunk_ids = await store_notion_chunks(user_query, notion_info)
    return chunk_ids[0] if chunk_ids else str(uuid.uuid4())

"""
chromaから類似情報を検索
Top-nの中から最もスコアが高いものを採用
"""
async def find_similar_notion_info(user_query: str, collections: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    try:
        notion_collection = collections.get("collection")

        # 検索結果の最大件数
        n_results = 20

        # ユーザークエリから直接クエリを実行
        query_embedding = await get_embeddings(user_query)

        # 類似したチャンクを検索
        results = notion_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
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

        for i, (distance, metadata) in enumerate(zip(distances, metadatas)):
            # 類似度を計算（距離を類似度に変換）
            similarity = 1.0 - distance
            page_id = metadata.get("notion_page_id", "")

            if not page_id:
                continue

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

"""
Notion情報をチャンクに分割して保存
Args:
    user_query: ユーザーからの質問
    notion_info: Notionから取得した情報
Returns:
    生成されたチャンクIDのリスト
"""
async def store_notion_chunks(user_query: str, notion_info: Dict) -> List[str]:
    try:
        # デフォルト値の使用
        chunk_size = DEFAULT_CHUNK_SIZE
        overlap = DEFAULT_CHUNK_OVERLAP

        # タイトルの処理
        notion_title = notion_info.get("title", "")
        if not notion_title:
            # タイトルがない場合はコンテンツの最初の行をタイトルとして使用
            content = notion_info.get("content", "")
            if content:
                first_line = content.split("\n")[0][:50]  # 最初の行を最大50文字まで
                notion_title = first_line

        # コンテンツをチャンクに分割
        content = notion_info.get("content", "")
        chunks = await chunk_text(content, chunk_size, overlap)

        # 最大チャンク数を制限
        max_chunks = 20
        if len(chunks) > max_chunks:
            chunks = chunks[:max_chunks]

        # チャンクがない場合は空で作成
        if not chunks:
            chunks = [""]

        chunk_ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            # チャンクIDの生成
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)

            # メタデータの準備
            metadata = {
                "query": user_query,
                "notion_title": notion_title,
                "notion_page_id": notion_info.get("page_id", ""),
                "notion_url": notion_info.get("url", ""),
                "timestamp": datetime.now().isoformat(),
                "chunk_index": i,
                "total_chunks": len(chunks)
            }

            # チャンクの内容をメタデータに追加
            metadata["notion_content_chunk"] = chunk

            # 検索用テキスト（ユーザークエリとNotionタイトルを結合）
            combined_text = f"{user_query}\n{notion_title}\n{chunk}"

            # テキストのエンベディングを取得
            embedding = await get_embeddings(combined_text)

            embeddings.append(embedding)
            documents.append(combined_text)
            metadatas.append(metadata)

        # Notionコレクションを取得または作成
        notion_collection = client.get_or_create_collection("notion_info")

        # ChromaDBに保存
        notion_collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        return chunk_ids

    except Exception as e:
        logger.error(f"Notionチャンク保存中にエラー: {str(e)}", exc_info=True)
        return []

"""
テキストを指定されたサイズのチャンクに分割
"""
async def chunk_text(text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:

    # デフォルト値の使用
    chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
    overlap = overlap or DEFAULT_CHUNK_OVERLAP

    if not text:
        return [""]

    chunks = []
    text_length = len(text)

    # テキストが短い場合は分割せずに返す
    if text_length <= chunk_size:
        return [text]

    # 重複を考慮してチャンクに分割
    start = 0
    while start < text_length:
        end = start + chunk_size

        # テキストの終わりを超えないように調整
        if end > text_length:
            end = text_length

        chunks.append(text[start:end])

        # 次のチャンクの開始位置を計算（重複を考慮）
        start = end - overlap

        # 終了条件: スタート位置が終了位置を超えるか、テキストの終わりに達した場合
        if start >= end or end >= text_length:
            break

    return chunks
