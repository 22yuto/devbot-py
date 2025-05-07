import os
from typing import Optional, Dict, List, Any
from openai import OpenAI
from app.db import find_similar_notion_info, store_notion_info, client, get_collection_info
from app.services.notion import notion
from app.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

class ChatService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
    
    def check_initialized(self):
        if not self.api_key:
            raise ValueError("OpenAI APIキーが設定されていません")
        if not self.client:
            raise ValueError("OpenAIクライアントの初期化に失敗しました")
    
    async def generate_response_with_notion(self, user_query: str) -> Dict[str, Any]:
        """
        Notionの情報に基づいて回答を生成
        Notion情報のチャンク検索のみを使用し、QAペア検索と保存は行いません
        類似度が0.2以下の場合は強制的に新しい情報を取得します
        
        Args:
            user_query: ユーザーからの質問
            force_refresh: Trueの場合、キャッシュを無視して常に新しい情報を取得
        
        Returns:
            生成された回答を含む辞書
        """
        self.check_initialized()
        
        try:
            # 強制更新のキーワードをチェック
            refresh_keywords = ["更新", "最新", "新しい情報", "refresh"]
            has_refresh_keyword = any(keyword in user_query for keyword in refresh_keywords)
            
            
            # 環境変数から閾値を取得
            notion_similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.65"))
            # 最低類似度閾値 - これ以下なら強制的に更新
            min_similarity_threshold = float(os.getenv("MIN_SIMILARITY_THRESHOLD", "0.2"))
            
            notion_info = None
            from_cache = False
            similarity = 0.0
            
            # Notionチャンク検索
            try:
                # dbから取得
                collection_info = await get_collection_info("notion_info")
                
                if collection_info["has_data"]:
                    logger.info(f"Notionコレクションから類似情報を検索中... (コレクションサイズ: {collection_info['size']}件)")
                    notion_result = await find_similar_notion_info(user_query)
                    
                    if notion_result:
                        similarity = notion_result.get("similarity", 0)
                        original_query = notion_result.get("original_query", "")
                        
                        # 類似度が最低閾値を下回る場合は新しい情報を取得
                        if similarity <= min_similarity_threshold:
                            notion_info = None
                        else:
                            notion_info = notion_result.get("notion_info")
            except Exception as e:
                logger.warning(f"Notion情報の検索中にエラー: {str(e)}")
            
            
            # Notion情報が見つからなければ新たに検索
            if not notion_info:
                notion_info = await notion.find_best_matching_content(user_query)
                
                # 情報をチャンク分割して保存
                if notion_info:
                    title = notion_info.get("title", "")
                    content_len = len(notion_info.get("content", ""))
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
    
    async def generate_response(self, user_query: str, notion_info: Optional[Dict]) -> str:
        """
        Notion情報に基づいてレスポンスを生成
        チャンク分割された長い情報も適切に処理
        """
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
            max_content_length = 14000  # GPT-3.5-turboの最大コンテキスト長を考慮した安全な値
            
            if content_length > max_content_length:
                logger.info(f"コンテンツが長いため、切り詰めます: {content_length} -> {max_content_length}文字")
                # コンテンツを切り詰める（先頭部分を優先）
                truncated_content = content[:max_content_length] + "...(以下省略)"
            else:
                truncated_content = content
            
            # プロンプトの作成
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
            
            # OpenAIを使用してレスポンスを生成
            logger.info(f"OpenAIを使用してレスポンスを生成中...")
            
            # タイムアウト設定を追加
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",  # より大きなコンテキストウィンドウを持つモデルを使用
                messages=[
                    {"role": "system", "content": "あなたはNotionの情報を基にした質問回答システムです。与えられた情報のみに基づいて簡潔に回答してください。"},
                    {"role": "user", "content": prompt}
                ],
                timeout=30.0  # 30秒のタイムアウト設定
            )
            
            if not response or not response.choices:
                logger.error("OpenAIからの応答が空または無効です")
                return "回答の生成中にエラーが発生しました。しばらく経ってからもう一度お試しください。"
                
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"応答生成中にエラー: {str(e)}", exc_info=True)
            return f"応答の生成中にエラーが発生しました: {str(e)[:100]}... お手数ですが、しばらく経ってからもう一度お試しください。"

# シングルトンとしてインスタンスを作成
chat = ChatService() 