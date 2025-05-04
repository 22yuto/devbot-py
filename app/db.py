from chromadb import Client

client = Client()

collection = client.create_collection("test")

collection.add(
    ids=["1", "2", "3"],
    documents=["Hello", "World", "Chromadb"],
)

# クエリで特定のデータを検索
results = collection.query(
    query_texts=["Hello"],
    n_results=2,
)

print("クエリ結果:")
print(results)

# コレクションの中身を全て取得
all_documents = collection.get()
print("\nコレクション内の全てのデータ:")
print(all_documents)