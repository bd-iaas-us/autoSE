# TODO: use code in rag.py instead of this script

import os

from haystack import Pipeline
from haystack.components.converters import TextFileToDocument
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

collection_name = "cannyls-go"
collection_path = "data/cannyls-go"

document_store = QdrantDocumentStore("127.0.0.1",
                                     recreate_index=True,
                                     return_embedding=True,
                                     wait_result_from_api=True,
                                     embedding_dim=1024,
                                     index=collection_name)

doc_embedder = SentenceTransformersDocumentEmbedder(
    model="WhereIsAI/UAE-Large-V1")  #use default embedding model


def find_files(directory, filter_func):
    results = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if filter_func(file):
                results.append(os.path.join(root, file))
    return results


#walk thought data path to get all .go files.
def is_go_file(filename):
    return filename.endswith('.go')


file_names = find_files(collection_path, is_go_file)

pipeline = Pipeline()
pipeline.add_component("converter", TextFileToDocument())
pipeline.add_component("splitter",
                       DocumentSplitter(split_by="word", split_length=200))
pipeline.add_component(name="embedder", instance=doc_embedder)
pipeline.add_component(
    "writer",
    DocumentWriter(document_store=document_store,
                   policy=DuplicatePolicy.OVERWRITE))

#convert => splitter => embedder => document_store
pipeline.connect("converter.documents", "splitter")
pipeline.connect("splitter.documents", "embedder")
pipeline.connect("embedder.documents", "writer")
pipeline.run({"converter": {"sources": file_names}})
