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

if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY環境変数が設定されていません")
if not os.getenv("NOTION_API_KEY"):
    logger.warning("NOTION_API_KEY環境変数が設定されていません")
if not os.getenv("NOTION_DATABASE_ID"):
    logger.warning("NOTION_DATABASE_ID環境変数が設定されていません")

# デフォルト値を設定
if not os.getenv("SIMILARITY_THRESHOLD"):
    os.environ["SIMILARITY_THRESHOLD"] = "0.85"
    logger.info(f"SIMILARITY_THRESHOLD環境変数が未設定のため、デフォルト値 {os.getenv('SIMILARITY_THRESHOLD')} を使用します")
else:
    logger.info(f"SIMILARITY_THRESHOLD環境変数: {os.getenv('SIMILARITY_THRESHOLD')}")

# FastAPI初期化
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(router, prefix="/api")
