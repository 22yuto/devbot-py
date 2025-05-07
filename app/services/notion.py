import os
from typing import Optional, Dict, List, Any
from fastapi import HTTPException
from notion_client import Client
from app.db import get_embeddings
from app.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

class NotionService:
    def __init__(self):
        self.api_key = os.getenv("NOTION_API_KEY")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.client = Client(auth=self.api_key) if self.api_key else None
    
    def check_initialized(self):
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Notion APIキーが設定されていません")
        if not self.database_id:
            raise HTTPException(status_code=500, detail="NotionデータベースIDが設定されていません")
        if not self.client:
            raise HTTPException(status_code=500, detail="Notionクライアントの初期化に失敗しました")
    
    async def fetch_database_content(self, database_id: Optional[str] = None, query: Optional[Dict] = None) -> List[Dict]:
        """
        Notionデータベースから情報を取得
        """
        self.check_initialized()
        
        try:
            db_id = database_id or self.database_id
            
            # queryパラメータの処理を修正
            if query is None:
                # フィルターなしでクエリ
                results = self.client.databases.query(database_id=db_id)
            else:
                # フィルター付きでクエリ
                results = self.client.databases.query(
                    database_id=db_id,
                    filter=query
                )
                
            return results["results"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Notionからのデータ取得に失敗: {str(e)}")
    
    async def fetch_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        ページIDから詳細なページコンテンツを取得する
        """
        self.check_initialized()
        
        try:
            # ページの基本情報を取得
            logger.info(f"ページID '{page_id}' の情報を取得します")
            page = self.client.pages.retrieve(page_id)
            
            # ページのブロック（コンテンツ）を取得
            logger.info(f"ページID '{page_id}' のブロックを取得します")
            blocks = self.client.blocks.children.list(block_id=page_id)
            
            # ページタイトルを取得（可能であれば）
            title = ""
            if page.get("properties"):
                for prop_name, prop_data in page.get("properties", {}).items():
                    prop_type = prop_data.get("type", "")
                    if prop_type == "title" and prop_data.get("title"):
                        for text_item in prop_data.get("title", []):
                            title += text_item.get("plain_text", "")
                        break
            
            # ブロックからテキストを抽出
            content = self.extract_blocks_content(blocks.get("results", []))
            
            return {
                "page_id": page_id,
                "title": title,
                "content": content,
                "url": page.get("url", "")
            }
        except Exception as e:
            logger.error(f"ページID '{page_id}' の内容取得中にエラー: {str(e)}")
            return {
                "page_id": page_id,
                "title": "",
                "content": "",
                "url": ""
            }
    
    def extract_blocks_content(self, blocks: List[Dict]) -> str:
        """
        ブロックのリストからテキストコンテンツを抽出
        """
        content = ""
        
        for block in blocks:
            block_type = block.get("type", "")
            
            if block_type == "paragraph":
                content += self.extract_rich_text(block.get("paragraph", {}).get("rich_text", [])) + "\n\n"
            
            elif block_type == "heading_1":
                text = self.extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
                content += f"# {text}\n\n"
            
            elif block_type == "heading_2":
                text = self.extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
                content += f"## {text}\n\n"
            
            elif block_type == "heading_3":
                text = self.extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
                content += f"### {text}\n\n"
            
            elif block_type == "bulleted_list_item":
                text = self.extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
                content += f"• {text}\n"
            
            elif block_type == "numbered_list_item":
                text = self.extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
                content += f"1. {text}\n"
            
            elif block_type == "to_do":
                todo_data = block.get("to_do", {})
                checked = "✅ " if todo_data.get("checked", False) else "☐ "
                text = self.extract_rich_text(todo_data.get("rich_text", []))
                content += f"{checked}{text}\n"
            
            elif block_type == "toggle":
                text = self.extract_rich_text(block.get("toggle", {}).get("rich_text", []))
                content += f"▶ {text}\n"
            
            elif block_type == "code":
                code_data = block.get("code", {})
                language = code_data.get("language", "")
                text = self.extract_rich_text(code_data.get("rich_text", []))
                content += f"```{language}\n{text}\n```\n\n"
            
            elif block_type == "quote":
                text = self.extract_rich_text(block.get("quote", {}).get("rich_text", []))
                content += f"> {text}\n\n"
            
            elif block_type == "callout":
                text = self.extract_rich_text(block.get("callout", {}).get("rich_text", []))
                emoji = block.get("callout", {}).get("icon", {}).get("emoji", "💡")
                content += f"{emoji} {text}\n\n"
            
            # 子ブロックがある場合は再帰的に処理
            if block.get("has_children", False):
                try:
                    child_blocks = self.client.blocks.children.list(block_id=block.get("id"))
                    child_content = self.extract_blocks_content(child_blocks.get("results", []))
                    content += child_content
                except Exception as e:
                    logger.error(f"子ブロックの取得中にエラー: {str(e)}")
        
        return content
    
    def extract_rich_text(self, rich_text_list: List[Dict]) -> str:
        """
        リッチテキストのリストからプレーンテキストを抽出
        """
        text = ""
        for text_item in rich_text_list:
            text += text_item.get("plain_text", "")
        return text
    
    def extract_page_content(self, page: Dict) -> Dict[str, str]:
        """
        Notionページから内容を抽出（データベースクエリ結果用）
        """
        try:
            title = ""
            content = ""
            
            # プロパティからタイトルを抽出
            for prop_name, prop_value in page.get("properties", {}).items():
                prop_type = prop_value.get("type", "")
                
                # タイトルプロパティを探す
                if prop_type == "title" and prop_value.get("title"):
                    # タイトルを抽出
                    for text_item in prop_value.get("title", []):
                        title += text_item.get("plain_text", "")
                
                # テキストプロパティも内容として追加
                elif prop_type == "rich_text" and prop_value.get("rich_text"):
                    prop_text = ""
                    for text_item in prop_value.get("rich_text"):
                        prop_text += text_item.get("plain_text", "")
                    
                    if prop_text:
                        content += f"{prop_name}: {prop_text}\n"
            
            # ページIDが利用可能なら、ページの完全な内容も非同期で取得できる
            # （このメソッドは同期的なため、ここでは行わない）
            
            return {
                "title": title,
                "content": content,
                "page_id": page.get("id"),
                "url": page.get("url", "")
            }
        except Exception as e:
            logger.error(f"ページコンテンツの抽出中にエラー: {str(e)}")
            return {"title": "", "content": "", "page_id": page.get("id", ""), "url": page.get("url", "")}
    
    async def search_pages(self, query: str) -> List[Dict]:
        """
        Notionの検索APIを使用してページを検索
        """
        self.check_initialized()
        
        try:
            logger.info(f"クエリ '{query}' で検索を実行します")
            search_results = self.client.search(query=query)
            
            logger.info(f"{len(search_results.get('results', []))}件の検索結果を取得しました")
            return search_results.get("results", [])
        except Exception as e:
            logger.error(f"検索中にエラー: {str(e)}")
            return []
    
    async def find_candidate_pages(self, user_query: str, notion_data: List[Dict], max_candidates: int = 3) -> List[Dict]:
        """
        ユーザークエリに関連する候補ページを見つける（簡易的な類似度計算）
        """
        # クエリのエンベディングを取得
        query_embedding = await get_embeddings(user_query)
        
        candidates = []
        
        # 各ページをチェック
        for item in notion_data:
            try:
                # ページコンテンツを抽出
                page_content = self.extract_page_content(item)
                
                # 処理するコンテンツがない場合はスキップ
                if not page_content["title"].strip() and not page_content["content"].strip():
                    continue
                
                # テキストを結合してエンベディング化
                combined_text = f"{page_content['title']} {page_content['content']}".strip()
                item_embedding = await get_embeddings(combined_text)
                
                # コサイン類似度を計算
                score = self.cosine_similarity(query_embedding, item_embedding)
                page_content["score"] = score
                
                candidates.append(page_content)
            
            except Exception as e:
                logger.error(f"候補ページの処理中にエラー: {str(e)}")
                continue
        
        # スコアで並べ替えて上位の候補を返す
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        return candidates[:max_candidates]
    
    async def find_best_page_with_content(self, user_query: str, candidate_pages: List[Dict]) -> Optional[Dict]:
        """
        候補ページから詳細なコンテンツを取得して最適なページを選択
        """
        if not candidate_pages:
            logger.info("候補ページがありません")
            return None
        
        # クエリのエンベディングを取得
        query_embedding = await get_embeddings(user_query)
        
        best_match = None
        best_score = -1
        
        # 各候補ページの詳細コンテンツを取得して評価
        for page in candidate_pages:
            try:
                page_id = page.get("page_id")
                if not page_id:
                    continue
                
                # ページの詳細コンテンツを取得
                logger.info(f"ページID '{page_id}' の詳細コンテンツを取得中...")
                detailed_content = await self.fetch_page_content(page_id)
                
                # タイトルがない場合は元のタイトルを使用
                if not detailed_content.get("title") and page.get("title"):
                    detailed_content["title"] = page.get("title")
                
                # 詳細なテキストコンテンツで類似度を再計算
                combined_text = f"{detailed_content['title']} {detailed_content['content']}".strip()
                
                # 詳細コンテンツが十分にある場合のみ処理
                if len(combined_text) > 20:
                    logger.info(f"ページ '{detailed_content['title']}' の詳細コンテンツを使用して類似度を計算中...")
                    item_embedding = await get_embeddings(combined_text)
                    
                    # コサイン類似度を計算
                    score = self.cosine_similarity(query_embedding, item_embedding)
                    detailed_content["score"] = score
                    
                    logger.info(f"ページ '{detailed_content['title']}' の類似度スコア: {score}")
                    
                    if score > best_score:
                        best_score = score
                        best_match = detailed_content
                else:
                    logger.info(f"ページ '{detailed_content['title']}' の詳細コンテンツが不十分です")
            
            except Exception as e:
                logger.error(f"詳細ページの処理中にエラー: {str(e)}")
                continue
        
        # スコアが低すぎる場合は関連情報なしとする
        if best_score < 0.3:
            logger.info(f"最高スコア ({best_score}) が閾値を下回っているため関連情報なしとします")
            return None
        
        return best_match
    
    async def find_relevant_info(self, user_query: str, notion_data: List[Dict]) -> Optional[Dict]:
        """
        ユーザークエリに関連するNotion情報を見つける（従来の方法）
        """
        # クエリのエンベディングを取得
        query_embedding = await get_embeddings(user_query)
        
        best_match = None
        best_score = -1
        
        logger.info(f"Notionページ数: {len(notion_data)}件")
        
        # 各ページをチェック
        for item in notion_data:
            try:
                # ページコンテンツを抽出
                page_content = self.extract_page_content(item)
                
                # 処理するコンテンツがない場合はスキップ
                if not page_content["title"].strip() and not page_content["content"].strip():
                    logger.debug(f"ページID '{page_content['page_id']}' はタイトルとコンテンツが空のためスキップします")
                    continue
                
                # テキストを結合してエンベディング化
                combined_text = f"{page_content['title']} {page_content['content']}".strip()
                item_embedding = await get_embeddings(combined_text)
                
                # コサイン類似度を計算
                score = self.cosine_similarity(query_embedding, item_embedding)
                logger.debug(f"ページ '{page_content['title']}' の類似度スコア: {score}")
                
                if score > best_score:
                    best_score = score
                    page_content["score"] = score
                    best_match = page_content
            
            except Exception as e:
                logger.error(f"項目の処理中にエラー: {str(e)}")
                continue
        
        # スコアが低すぎる場合は関連情報なしとする
        if best_score < 0.3:
            logger.info(f"最高スコア ({best_score}) が閾値を下回っているため関連情報なしとします")
            return None
            
        return best_match
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        2つのベクトル間のコサイン類似度を計算
        """
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        if magnitude1 * magnitude2 == 0:
            return 0
        return dot_product / (magnitude1 * magnitude2)
    
    async def find_best_matching_content(self, user_query: str) -> Optional[Dict]:
        """
        クエリに最も関連するコンテンツを検索する統合メソッド
        このメソッドは以下のステップで処理を行います：
        1. データベースからページ一覧を取得
        2. 単純な類似度計算で候補ページを特定
        3. 候補ページの詳細コンテンツを取得
        4. 詳細コンテンツで再度類似度を計算して最適なページを選択
        """
        try:
            logger.info(f"クエリ '{user_query}' に関連するコンテンツを検索中...")
            
            # 1. データベースからデータを取得
            notion_data = await self.fetch_database_content()
            logger.info(f"{len(notion_data)}件のデータを取得しました")
            
            # 2. 候補ページを絞り込む
            candidate_pages = await self.find_candidate_pages(user_query, notion_data, max_candidates=3)
            logger.info(f"{len(candidate_pages)}件の候補ページを特定しました")
            
            # 3 & 4. 候補ページの詳細コンテンツを取得して最適なページを選択
            best_match = await self.find_best_page_with_content(user_query, candidate_pages)
            
            if best_match:
                logger.info(f"最適なページが見つかりました: '{best_match['title']}'")
            else:
                logger.info("関連するコンテンツが見つかりませんでした")
                
            return best_match
            
        except Exception as e:
            logger.error(f"コンテンツ検索中にエラー: {str(e)}", exc_info=True)
            return None

# シングルトンとしてインスタンスを作成
notion = NotionService() 