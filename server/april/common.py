from haystack.dataclasses.document import Document
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack import Pipeline
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import ComponentDevice, Secret
from haystack import component
from typing import Union, List, Any, Optional



# bydefault use the same index for RAG
# we wil use topic for next version
INDEX_NAME="documents"
MODEL_ID = "WhereIsAI/UAE-Large-V1"

def get_text_embedder():
    "this embedder is used for querying the document store"
    return SentenceTransformersTextEmbedder(model=MODEL_ID, device=ComponentDevice.from_str("cpu"))

"""
pipeline can not share the same component. so we have to create instance on the fly
"""
def get_doc_embedder():
    "this embedder is used for writing documents to the document store"
    return SentenceTransformersDocumentEmbedder(model=MODEL_ID, device=ComponentDevice.from_str("cpu"))

def get_document_store():
    """
    return the document store
    """
    return QdrantDocumentStore(
        host="127.0.0.1",
        return_embedding=True,
        wait_result_from_api=True,
        embedding_dim=1024,
        index=INDEX_NAME
    )

is_warm_up = False
def initialize():
    global is_warm_up
    if not is_warm_up:
        SentenceTransformersDocumentEmbedder(model=MODEL_ID, device=ComponentDevice.from_str("cpu")).warm_up()
        is_warm_up = True
    
initialize()

#add pytest

if __name__ == "__main__":

    print(get_document_store().count_documents())
    import time
    now = time.time()
    get_text_embedder()
    get_doc_embedder()
    print("this should be fast, beacause we already warmup", time.time()-now)
    print("done")
