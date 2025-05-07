PORT = 8002
run:
	uvicorn app.main:app --reload --port $(PORT)
# 有効化
venv:
	source venv/bin/activate
# venv依存パッケージのリスト出力
freeze:
	pip freeze > requirements.txt
# chromaサーバー起動
# chroma run --host localhost --port 8100