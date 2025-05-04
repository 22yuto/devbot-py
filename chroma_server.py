import chromadb
from chromadb.config import Settings

if __name__ == "__main__":
    print("ChromaDBサーバーを起動しています...")
    print("Ctrl+Cで終了できます")

    # サーバーの設定
    settings = Settings(
        chroma_api_impl="chromadb.api.fastapi.FastAPI",
        chroma_server_host="localhost",
        chroma_server_http_port=8000,
        persist_directory="./chroma_db"
    )

    # サーバーインスタンスを作成して実行
    server = chromadb.Client(settings)

    # 注意: このクライアントはサーバーを内部で起動します
    # 確認のためにコレクション一覧を取得してみる
    collections = server.list_collections()
    print(f"利用可能なコレクション: {[col.name for col in collections]}")

    # コンソールを保持して終了しないようにする
    print("サーバーが起動しました。このターミナルは開いたままにしてください。")
    print("Streamlitアプリを別のターミナルで起動してください。")

    try:
        # ユーザーが中断するまで実行を継続
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("サーバーを停止します...")
