import os
from openai import OpenAI

client = OpenAI()
import dotenv
dotenv.load_dotenv()

class OpenAITextEmbedModel:
    def __init__(self):
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

    def embed_text(self, text: str):
        try:
            response = client.embeddings.create(input=text,
            model=self.embedding_model)
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"OpenAI APIエラー: {e}") from e

if __name__ == '__main__':

    embedder = OpenAITextEmbedModel()
    test_text = "これはテスト用のテキストです。"
    embedding = embedder.embed_text(test_text)
    print(len(embedding)) # 3072
