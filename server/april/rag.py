from haystack import Document
from haystack import Pipeline
from haystack.components.writers import DocumentWriter
from haystack.components.preprocessors import DocumentSplitter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack.utils import ComponentDevice, Secret

from common import get_doc_embedder, get_text_embedder, get_document_store

from typing import Any, Callable, Dict, List, Optional, Union
from logger import init_logger
logger = init_logger(__name__)

class RagDocuments(object):
    def __init__(self):
        pass
    
    def register_docs(self, docs: List[str]):
        logger.debug(f"register docs: {docs}")
        # Define the processing pipeline
        pipeline = Pipeline()
        pipeline.add_component("splitter", DocumentSplitter(split_by="word", split_length=200))
        pipeline.add_component("doc_embedder", get_doc_embedder())
        pipeline.add_component("writer",
                               DocumentWriter(document_store=get_document_store(), policy=DuplicatePolicy.OVERWRITE))

        # Connect the components
        pipeline.connect("splitter.documents", "doc_embedder")
        pipeline.connect("doc_embedder.documents", "writer")

        # Process documents through the pipeline
        result = pipeline.run({"splitter": {"documents":[Document(content=doc) for doc in docs]}})
        logger.debug(f"register docs result: {result}")

    def get_doc(self, hint: str) -> List[str]:
        pipeline = Pipeline()
        pipeline.add_component("text_embedder", get_text_embedder())
        pipeline.add_component("retriever", QdrantEmbeddingRetriever(document_store=get_document_store()))
        pipeline.connect("text_embedder", "retriever.query_embedding")
        retrieved_docs = pipeline.run({"text_embedder": {"text": hint}})

        retrieved_docs = retrieved_docs["retriever"]["documents"]
        logger.debug(f"RAG: {retrieved_docs}")
        return [doc.content for doc in retrieved_docs]


if __name__ == "__main__":
    rag = RagDocuments()
    rag.register_docs(["hello world", "hello python", "apple"])
    print(rag.get_doc("python"))
    print("done")