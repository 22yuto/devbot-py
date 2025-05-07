import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.router import router
from dotenv import load_dotenv
from app.logger import setup_logger, get_logger

# 環境変数のロード
load_dotenv()

# ロギング設定
setup_logger()
logger = get_logger(__name__)

logger.info("環境変数を読み込みました")

# APIキーのチェック
if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY環境変数が設定されていません")
if not os.getenv("NOTION_API_KEY"):
    logger.warning("NOTION_API_KEY環境変数が設定されていません")
if not os.getenv("NOTION_DATABASE_ID"):
    logger.warning("NOTION_DATABASE_ID環境変数が設定されていません")

# オプション設定のデフォルト値を設定
if not os.getenv("SIMILARITY_THRESHOLD"):
    os.environ["SIMILARITY_THRESHOLD"] = "0.85"
    logger.info(f"SIMILARITY_THRESHOLD環境変数が未設定のため、デフォルト値 {os.getenv('SIMILARITY_THRESHOLD')} を使用します")
else:
    logger.info(f"SIMILARITY_THRESHOLD環境変数: {os.getenv('SIMILARITY_THRESHOLD')}")

# FastAPIアプリケーションの初期化
app = FastAPI()

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(router, prefix="/api")

# @app.on_event("startup")
# async def startup_event():
#     """
#     アプリケーション起動時の処理
#     """
#     logger.info("アプリケーションを起動しました")
    
#     # 利用可能なエンドポイントをログに出力
#     endpoints = [
#         {"path": route.path, "name": route.name, "methods": route.methods}
#         for route in app.routes
#     ]
#     logger.info(f"利用可能なエンドポイント: {endpoints}")
#     logger.info("サーバーの準備が完了しました")
