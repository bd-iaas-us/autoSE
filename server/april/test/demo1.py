# Load Data
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.vllm import VllmServer
from llama_index.vector_stores.qdrant import QdrantVectorStore

import qdrant_client


#documents = SimpleDirectoryReader("data/jedi/", recursive=True).load_data()

#print(len(documents))
# vllm load model
# use this to test vllm server
# curl -XPOST http://localhost:8000/generate -d'{"prompt":"hello"}'
llm = VllmServer(
   api_url="http://localhost:8000/generate", max_new_tokens=100, temperature=0
)

# TODO: change Embedding model to text-embeddings-inference
Settings.embed_model = HuggingFaceEmbedding(model_name="WhereIsAI/UAE-Large-V1", device="cpu")
Settings.llm = llm

client = qdrant_client.QdrantClient(
    url = "http://localhost:6333",
)
vector_store = QdrantVectorStore(client=client, collection_name="paul_graham")
index = VectorStoreIndex.from_vector_store(vector_store)

query_engine = index.as_query_engine()

querys = ["What did the author do growing up?"]
for q in querys:
    response = query_engine.query(q)
    print(response)

