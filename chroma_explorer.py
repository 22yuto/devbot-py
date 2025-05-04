import streamlit as st
import chromadb
import os
import json

st.set_page_config(page_title="ChromaDB Explorer", layout="wide")

st.title("ChromaDB Explorer")

# DBパスの設定
db_path = st.text_input("ChromaDBのパス", value="./chroma_db")

# サーバー接続設定
st.sidebar.header("サーバー設定")
use_server = st.sidebar.checkbox("サーバーモードを使用", value=True)
server_host = st.sidebar.text_input("サーバーホスト", value="localhost")
server_port = st.sidebar.text_input("サーバーポート", value="8000")

# サイドバー: 操作選択
with st.sidebar:
    st.header("操作")
    operation = st.radio(
        "実行する操作を選択してください",
        ["既存DBの閲覧", "新しいデータの追加"]
    )

# メイン画面
if st.button("ChromaDBに接続"):
    try:
        # DBに接続（サーバーモードかローカルモードを選択）
        if use_server:
            # HTTPクライアントとして接続
            client = chromadb.HttpClient(host=server_host, port=server_port)
            st.success(f"ChromaDBサーバー {server_host}:{server_port} に接続しました")
        else:
            # 従来のローカルクライアントとして接続（非推奨）
            client = chromadb.PersistentClient(path=db_path)
            st.success(f"ローカルChromaDB {db_path} に接続しました")

        # コレクション一覧
        collections = client.list_collections()
        collection_names = [col.name for col in collections]

        if not collection_names:
            st.warning("コレクションが見つかりません。新しいコレクションを作成します。")
            new_collection_name = st.text_input("新しいコレクション名", value="my_collection")
            if st.button("コレクション作成"):
                client.create_collection(name=new_collection_name)
                st.success(f"コレクション '{new_collection_name}' を作成しました！")
                st.experimental_rerun()
        else:
            # コレクション選択
            selected_collection = st.selectbox("コレクションを選択", collection_names)

            if selected_collection:
                collection = client.get_collection(selected_collection)

                if operation == "既存DBの閲覧":
                    # データ取得
                    try:
                        data = collection.get()

                        # タブで表示を分ける
                        tab1, tab2 = st.tabs(["ドキュメント一覧", "検索"])

                        with tab1:
                            if not data["documents"]:
                                st.info("ドキュメントがありません")
                            else:
                                st.write(f"合計: {len(data['documents'])} ドキュメント")
                                for i, (doc, metadata, id) in enumerate(zip(data["documents"], data["metadatas"], data["ids"])):
                                    with st.expander(f"ドキュメント ID: {id}"):
                                        st.write("**内容:**")
                                        st.write(doc)
                                        st.write("**メタデータ:**")
                                        st.json(metadata)

                        with tab2:
                            query = st.text_input("検索クエリを入力")
                            n_results = st.slider("表示件数", min_value=1, max_value=20, value=5)

                            if query and st.button("検索"):
                                results = collection.query(query_texts=[query], n_results=n_results)

                                if not results["documents"][0]:
                                    st.info("検索結果がありません")
                                else:
                                    for i, (doc, metadata, id, distance) in enumerate(zip(
                                        results["documents"][0],
                                        results["metadatas"][0],
                                        results["ids"][0],
                                        results["distances"][0]
                                    )):
                                        with st.expander(f"結果 #{i+1} - ID: {id} (類似度: {1-distance:.4f})"):
                                            st.write("**内容:**")
                                            st.write(doc)
                                            st.write("**メタデータ:**")
                                            st.json(metadata)

                    except Exception as e:
                        st.error(f"データ取得中にエラーが発生しました: {str(e)}")

                elif operation == "新しいデータの追加":
                    st.header("新しいドキュメントの追加")

                    # 入力フォーム
                    with st.form("add_document_form"):
                        doc_id = st.text_input("ドキュメントID (空欄の場合は自動生成)")
                        doc_content = st.text_area("ドキュメント内容", height=200)
                        doc_metadata = st.text_area("メタデータ (JSON形式)", value="{}", height=100)

                        submitted = st.form_submit_button("登録")

                        if submitted:
                            try:
                                # メタデータをJSONとしてパース
                                metadata = json.loads(doc_metadata)

                                # IDの処理
                                if not doc_id:
                                    import uuid
                                    doc_id = str(uuid.uuid4())

                                # ドキュメント追加
                                collection.add(
                                    documents=[doc_content],
                                    metadatas=[metadata],
                                    ids=[doc_id]
                                )

                                st.success(f"ドキュメントを追加しました！ID: {doc_id}")
                            except json.JSONDecodeError:
                                st.error("メタデータが正しいJSON形式ではありません。")
                            except Exception as e:
                                st.error(f"ドキュメント追加中にエラーが発生しました: {str(e)}")

    except Exception as e:
        st.error(f"ChromaDBへの接続中にエラーが発生しました: {str(e)}")
else:
    st.info("「ChromaDBに接続」ボタンをクリックして接続を開始してください")
    st.warning("注意: サーバーモードを使用する場合は、まず別ターミナルで `python chroma_server.py` を実行してChromaDBサーバーを起動してください")
