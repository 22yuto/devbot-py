import os
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from app.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

# .envファイルの読み込み
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    logger.warning(".env ファイルが見つかりません")

# OpenAIクライアントの初期化（環境変数から直接取得）
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

async def get_embeddings(text: str) -> List[float]:
    """
    OpenAIのAPIを使用してテキストのエンベディングを取得

    Args:
        text: エンベディングを生成するテキスト

    Returns:
        生成されたエンベディングベクトル
    """
    try:
        response = openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"エンベディング生成中にエラーが発生しました: {str(e)}")
        raise

async def generate_completion(
    prompt: str,
    system_message: str = "あなたは役立つAIアシスタントです。",
    model: str = "gpt-3.5-turbo-16k",
    temperature: float = 0.7,
    max_tokens: int = None,
    timeout: float = 30.0
) -> str:
    """
    OpenAIのAPIを使用してテキスト生成を行う

    Args:
        prompt: ユーザープロンプト
        system_message: システムメッセージ
        model: 使用するモデル
        temperature: 生成の多様性（0-1）
        max_tokens: 最大トークン数（Noneの場合はモデルのデフォルト）
        timeout: タイムアウト（秒）

    Returns:
        生成されたテキスト
    """
    try:
        # APIパラメータの準備
        params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "timeout": timeout
        }

        # max_tokensが指定されている場合のみ追加
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        # OpenAI APIを呼び出し
        response = openai_client.chat.completions.create(**params)

        if not response or not response.choices:
            logger.error("OpenAIからの応答が空または無効です")
            return ""

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"テキスト生成中にエラーが発生しました: {str(e)}")
        raise
