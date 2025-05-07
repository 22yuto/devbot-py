import os
from typing import Optional, Dict, Any
from app.db import find_similar_notion_info, store_notion_info, get_collection_info
from app.services.notion import notion
from app.logger import get_logger
from app.utils.openai import generate_completion

logger = get_logger(__name__)

class ChatService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

    def check_initialized(self):
        if not self.api_key:
            raise ValueError("OpenAI APIキーが設定されていません")

    """
    Notion情報に基づいて回答を生成
    類似度が0.2以下の場合はnotionから新しい情報を取得
    """
    async def generate_response_with_notion(self, user_query: str) -> Dict[str, Any]:
        self.check_initialized()

        try:
            # 最低類似度閾値
            min_similarity_threshold = float(os.getenv("MIN_SIMILARITY_THRESHOLD", "0.2"))

            notion_info = None
            similarity = 0.0

            try:
                # chromaから取得
                collections = await get_collection_info("notion_info")

                if collections["has_data"]:
                    result = await find_similar_notion_info(user_query, collections)

                    if result:
                        similarity = result.get("similarity", 0)

                        # 類似度が最低閾値を下回る場合はNotionから新しい情報を取得
                        if similarity <= min_similarity_threshold:
                            notion_info = None
                        else:
                            notion_info = result.get("notion_info")
            except Exception as e:
                logger.warning(f"Notion情報の検索中にエラー: {str(e)}")

            # Notion情報が見つからなければ新たに検索
            if not notion_info:
                notion_info = await notion.find_best_matching_content(user_query)

                # 情報をチャンク分割して保存
                if notion_info:
                    chunk_ids = await store_notion_info(user_query, notion_info)
                    logger.info(f"Notion情報を{len(chunk_ids)}チャンクに分割して保存しました")
                else:
                    logger.warning("Notionから関連情報が見つかりませんでした")

            # 回答を生成
            response_text = await self.generate_response(user_query, notion_info)

            # レスポンスを構築
            source = notion_info.get("title", "") if notion_info else "情報なし"
            url = notion_info.get("url", "") if notion_info else ""

            result = {
                "message": response_text,
                "source": source,
                "url": url,
                "similarity": similarity
            }

            return result

        except Exception as e:
            logger.error(f"レスポンス生成中にエラー: {str(e)}", exc_info=True)
            return {
                "message": "エラーが発生しました。",
                "success": False,
                "error": str(e),
                "from_cache": False
            }

    """
    Notion情報に基づいてレスポンスを生成
    チャンク分割された長い情報も適切に処理
    """
    async def generate_response(self, user_query: str, notion_info: Optional[Dict]) -> str:
        self.check_initialized()

        if not notion_info:
            return "関連する情報が見つかりませんでした。もう少し具体的な質問をいただけますか？"

        try:
            # コンテンツの長さを確認
            content = notion_info.get('content', '')
            if not content:
                logger.warning("Notion情報のコンテンツが空です")
                return "取得した情報に本文が含まれていないため、回答を生成できません。検索条件を変更してお試しください。"

            content_length = len(content)

            # 詳細な内容があるか確認
            has_detailed_content = content_length > 100
            content_type = "詳細なページ内容" if has_detailed_content else "データベースの情報"

            logger.info(f"レスポンス生成に使用するコンテンツ: {content_length}文字")

            # 長いコンテンツを扱うためのトークン制限を考慮
            max_content_length = 14000

            if content_length > max_content_length:
                # コンテンツを切り詰める（先頭部分を優先）
                truncated_content = content[:max_content_length] + "...(以下省略)"
            else:
                truncated_content = content

            prompt = f"""
            ユーザーの質問: {user_query}

            参考情報 ({content_type}):
            タイトル: {notion_info.get('title', '')}
            内容: {truncated_content}

            上記の参考情報に基づいて、ユーザーの質問に対する適切で具体的な回答を生成してください。
            回答はシンプルで直接的に、かつ参考情報の内容に忠実に作成してください。
            質問に直接関係する情報がない場合は正直に「この質問に答えるための十分な情報がありません」と伝えてください。
            回答を始める際に「Notionのデータによると」などのフレーズは不要です。
            """

            system_message = "あなたはNotionの情報を基にした質問回答システムです。与えられた情報のみに基づいて簡潔に回答してください。"

            response_text = await generate_completion(
                prompt=prompt,
                system_message=system_message,
                model="gpt-3.5-turbo-16k",
                temperature=0.7,
                timeout=30.0
            )

            if not response_text:
                logger.error("レスポンス生成に失敗しました")
                return "回答の生成中にエラーが発生しました。しばらく経ってからもう一度お試しください。"

            return response_text

        except Exception as e:
            logger.error(f"応答生成中にエラー: {str(e)}", exc_info=True)
            return f"応答の生成中にエラーが発生しました: {str(e)[:100]}... お手数ですが、しばらく経ってからもう一度お試しください。"

# シングルトンとしてインスタンスを作成
chat = ChatService()
