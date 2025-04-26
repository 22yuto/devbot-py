# RAGの流れ
import os
from openai import OpenAI
# slearn.metrics.pairwiseモジュールのcosine_similarity関数を使用
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from utils import vectorize_text
from utils import find_most_similar
from utils import ask_question

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI()

text = "2023年上期売上200億円、下期売上300億円"
question = "2023年の第一事業部の売り上げはどのくらい？"
documents = [
    "2023年上期売り上げ200億円、下期売上300億円",
    "2023年第一事業部売上300億円, 第二事業部売上150億円, 第三事業部売上50億円",
    "2024年は全社で1000億円の売上を目指す"
]

'''
質問に対して情報をベクトル化して類似度を求める
'''
# ドキュメントと質問をベクトル化
vectors = [vectorize_text(doc) for doc in documents]
question_vector = vectorize_text(question)

# 類似度の高い回答を導き出す
documents = find_most_similar(question_vector, vectors, documents)

answer = ask_question(question, documents)
print(answer)
# dbから質問に対して情報をベクトル化して類似度を求めて、コンテキストとしてチャットボットに入れてあげると、適切な回答を出してくれる