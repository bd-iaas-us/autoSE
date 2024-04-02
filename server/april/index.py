# Load Data
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.vllm import VllmServer
from llama_index.vector_stores.qdrant import QdrantVectorStore

import qdrant_client
import requests


# vllm load model
# use this to test vllm server
# curl -XPOST http://localhost:8000/generate -d'{"prompt":"hello"}'
llm = VllmServer(
   api_url="http://localhost:8000/generate", max_new_tokens=256, temperature=0
)

# TODO: change Embedding model to text-embeddings-inference
# I leave all 8 GPUs to LLM, so embeddings has to use cpu
Settings.embed_model = HuggingFaceEmbedding(model_name="WhereIsAI/UAE-Large-V1", device="cpu")
Settings.llm = llm

client = qdrant_client.QdrantClient(
    url = "http://localhost:6333",
)

topics = ["jedi", "faust", "rider"]
#TODO query engines should be a class.
query_engines = {}
for topic in topics:
    vector_store = QdrantVectorStore(client=client, collection_name=topic)
    index = VectorStoreIndex.from_vector_store(vector_store)
    query_engines[topic] = index.as_query_engine()


def general_query(query: str):
    response = requests.post("http://localhost:8000/generate", {"prompt": query, "max_new_tokens": 256, "temperature": 0})
    return response

if __name__ == "__main__":
    querys = ["how apiserver talk to scheduler?", "how to to create an instance in helium?", "grpc是什么"]
    for q in querys:
        response = query_engine.query(q)
        print(response)
