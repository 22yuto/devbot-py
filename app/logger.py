import logging
import os
from typing import Optional

"""
アプリケーション全体のロギング設定を初期化します
"""
def setup_logger(level: Optional[int] = None):
    # 環境変数からログレベルを取得（設定されていない場合はINFO）
    if level is None:
        log_level_str = os.getenv("LOG_LEVEL", "INFO")
        level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # 基本設定
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # 既存の設定を上書き
    )
    
    # 各モジュールのログレベルを設定（必要に応じて）
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

"""
指定された名前のロガーを取得します
"""
def get_logger(name: str):
    return logging.getLogger(name) 