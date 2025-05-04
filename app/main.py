from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.router import router

app = FastAPI()

# CORSの設定（Next.jsからのリクエストを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境ではNext.jsのドメインに制限することをお勧めします
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(router, prefix="/api")
