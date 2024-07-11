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


class RagDocument(object):
    def __init__(self):
        pass
    
    def register_doc(self, doc: str, topic: str, document_name: str):
        logger.debug(f"register doc: {doc}")

        # Get the document store
        document_store = get_document_store()

        # Check if a document with the same name already exists
        filters = {"operator": "AND",
                   "conditions": [
                       {"field": "meta.topic", "operator": "==", "value": topic},
                       {"field": "meta.document_name", "operator": "==", "value": document_name}
                   ]
                   }
        existing_docs = document_store.filter_documents(filters)

        if existing_docs:
            logger.error(f"Document with name '{document_name}' already exists.")
            raise ValueError(f"Document with name '{document_name}' already exists.")

        # Define the processing pipeline
        pipeline = Pipeline()
        pipeline.add_component("splitter", DocumentSplitter(split_by="word", split_length=5000))
        pipeline.add_component("doc_embedder", get_doc_embedder())
        pipeline.add_component("writer",
                               DocumentWriter(document_store=get_document_store(), policy=DuplicatePolicy.OVERWRITE))

        # Connect the components
        pipeline.connect("splitter.documents", "doc_embedder")
        pipeline.connect("doc_embedder.documents", "writer")

        # Process documents through the pipeline
        document = Document(content=doc, meta={"topic": topic, "document_name": document_name})
        result = pipeline.run({"splitter": {"documents": [document]}})
        logger.debug(f"register docs result: {result}")

    def get_docs(self, hint: str, topic: str) -> List[str]:
        pipeline = Pipeline()
        pipeline.add_component("text_embedder", get_text_embedder())
        filters = {"field": "meta.topic", "operator": "==", "value": topic}
        pipeline.add_component("retriever", QdrantEmbeddingRetriever(document_store=get_document_store(),
                                                                     filters=filters))
        pipeline.connect("text_embedder", "retriever.query_embedding")
        retrieved_docs = pipeline.run({"text_embedder": {"text": hint}})

        retrieved_docs = retrieved_docs["retriever"]["documents"]
        logger.debug(f"RAG: {retrieved_docs}")
        return [doc.content for doc in retrieved_docs]
    
    def list_docs(self):
        """
        list docs is used by ui.py, TODO: support paging on UI
        return at most 100
        """
        import qdrant_client
        from qdrant_client.http.models import ScrollRequest

        QDRANT_ADDR="http://localhost:6333"
        client = qdrant_client.QdrantClient(
            url = QDRANT_ADDR
        )
        from common import INDEX_NAME
        scroll_result = client.scroll(collection_name=INDEX_NAME,limit=100)
        return scroll_result[0]



if __name__ == "__main__":
    rag = RagDocument()
    rag.register_doc(doc="The current president of the United States is Joe Biden", topic="President",
                     document_name="President_Biden_1")
    print(rag.get_docs("Biden", "President"))
    print(rag.list_docs())
