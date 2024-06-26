from index import QueryLint, suppported_topics
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from haystack.dataclasses.document import Document
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack import Pipeline
from haystack.document_stores.types import DuplicatePolicy
from contextlib import asynccontextmanager
from typing import Union, List, Any, Optional
from pydantic import BaseModel


import uvicorn
import json
import asyncio

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
from issue import handle_prompt, handle_task, gen_history_data

from logger import init_logger
logger = init_logger(__name__)



def veriy_header(request: Request):
    if request.headers.get("Authorization") != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect API key",
            headers={"WWW-Authenticate": "Basic"})

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    logger.info("checking environment...")
    yield
    # Clean up the ML models and release the resources
    logger.info("quiting...")

app = FastAPI(lifespan=lifespan, logger=logger)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/supported_topics", dependencies=[Depends(veriy_header)])
async def supported_topics() -> Response:
    """
    Get the list of supported topics
    """
    return JSONResponse(status_code=200, content={"topics": suppported_topics()})


class RegisterRagRequest(BaseModel):
    docs: List[str]


class RegisterRagResponse(BaseModel):
    status: str
    message: str


# Rag Qdrant Document Store configuration
rag_collection_name = "documents"


@app.post("/rag", dependencies=[Depends(veriy_header)])
async def register_doc(request: RegisterRagRequest) -> RegisterRagResponse:
    try:
        # Initialize Qdrant Document Store
        document_store = QdrantDocumentStore(
            host="127.0.0.1",
            recreate_index=True,
            return_embedding=True,
            wait_result_from_api=True,
            embedding_dim=1024,
            index=rag_collection_name
        )
    except Exception as e:
        logger.error("Error initializing Qdrant Document Store: %s", e)
        raise HTTPException(status_code=500, detail="Failed to initialize document store.")

    logger.debug("Received request: %s", request)

    try:
        # Initialize the embedding model
        doc_embedder = SentenceTransformersDocumentEmbedder(model="WhereIsAI/UAE-Large-V1")
    except Exception as e:
        logger.error("Error initializing document embedder: %s", e)
        raise HTTPException(status_code=500, detail="Failed to initialize document embedder.")

    try:
        # Define the processing pipeline
        pipeline = Pipeline()
        pipeline.add_component("splitter", DocumentSplitter(split_by="word", split_length=200))
        pipeline.add_component("embedder", doc_embedder)
        pipeline.add_component("writer",
                               DocumentWriter(document_store=document_store, policy=DuplicatePolicy.OVERWRITE))

        # Connect the components
        pipeline.connect("splitter.documents", "embedder")
        pipeline.connect("embedder.documents", "writer")

        # Process documents through the pipeline
        pipeline.run({"splitter": {"documents":[Document(content=doc) for doc in request.docs]}})
        return RegisterRagResponse(status="success",
                                   message="Documents successfully registered in the vector database.")
    except Exception as e:
        logger.error("Error processing documents: %s", e)
        return RegisterRagResponse(status="error", message=str(e))


class DevRequest(BaseModel):
    prompt: str
    repo: str
    token: Optional[str] = None
    model: str

class DevResponse(BaseModel):
    task_id: str

@app.post("/dev", dependencies=[Depends(veriy_header)])
async def dev_task(request: DevRequest) -> DevResponse:
    """
    API for handle "dev" sub command
    Currently only the following tasks supported:
        1. Project based prompt:
        {
            "repo": "your repo url",
            "token": "you token to access the repo",
            "prompt": "your prompt"
        }
    """
    logger.debug(request)

    return DevResponse(task_id=handle_prompt(request))

class TaskStatus(BaseModel):
    status :str
    patch: Optional[str] = None

@app.get("/dev/tasks/{taskId}", dependencies=[Depends(veriy_header)])
async def getTaskStatus(taskId) -> TaskStatus:
    status, patch = handle_task(taskId)
    return TaskStatus(status=status, patch=patch)

    

@app.get("/dev/histories/{taskId}", dependencies=[Depends(veriy_header)])
async def getHistory(taskId, request: Request) -> StreamingResponse:
    return StreamingResponse(gen_history_data(taskId), media_type="text/plain")



class LintRequest(BaseModel):
    topic: str
    code: str
    """
    model should follow this format:
    org:model
    such as 
    openai:gpt4
    ...
    ollama:llama3
    """    
    model: str

class LintResponse(BaseModel):
    """
    backend is deprecated.
    """
    backend: Optional[str] = None
    plain_risks : str
    risks : List
    """
    model should follow this format:
    org:model
    such as 
    openai:gpt4
    ...
    ollama:llama3
    """    
    model: str


@app.post("/lint", dependencies=[Depends(veriy_header)])
async def query(req :LintRequest) -> LintResponse:
    """
    test: curl -X POST "http://127.0.0.1:8000/lint" -H "Content-Type: application/json" -d '{"topic": "your_topic", "code": "your_code"}'
    request: Lint
    response: {}
    """
    logger.debug(LintRequest)
    try: 
        model = req.model
        ai = "openai"
        #FIXME: QueryLint should support choosing models
        llm_response = QueryLint(ai).query_lint(req.topic, req.code)
    except Exception as e:
        raise HTTPException(status_code=500, detail = f"{e}")

    response = LintResponse(model="openai:gpt3.5", plain_risks="", risks=[])
    if model.startswith("openai"):
        #llm_respnose is json-encode string returned from openai
        #response = {"risks":[{"which_part_of_code":"here", "reason":"why", "fix":"how"}, {"which_part_of_code":"here1", "reason":"why2", "fix":"how2"}]}
        response.backend = ai
        response.plain_risks = ""
        response.risks = json.loads(llm_response)["risks"]
        logger.debug(response)
    else:
        response.backend = ai
        response.plain_risks = llm_response
        response.risks = []
    return response


#uvicorn --reload --port 8000 api:app
#TODO add arguments
if __name__ == "__main__":
    #asyncio.run(WebSocketServer())
    uvicorn.run(app, host="127.0.0.1", port=8000)
