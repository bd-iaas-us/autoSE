from index import QueryLint, suppported_topics
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from contextlib import asynccontextmanager
from typing import Union, List, Any
from pydantic import BaseModel

import uvicorn
import json
import asyncio

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os

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


class LintRequest(BaseModel):
    topic: str
    code: str

class LintResponse(BaseModel):
    backend: str
    plain_risks : str
    risks : List

@app.post("/lint", dependencies=[Depends(veriy_header)])
async def query(req :LintRequest) -> LintResponse:
    """
    test: curl -X POST "http://127.0.0.1:8000/lint" -H "Content-Type: application/json" -d '{"topic": "your_topic", "code": "your_code"}'
    request: Lint
    response: {}
    """
    logger.debug(LintRequest)
    try: 
        ai = os.environ["AI_BACKEND"]
        llm_response = QueryLint(ai).query_lint(req.topic, req.code)
        #llm_response = '''{"risks":[{"which_part_of_code":"here", "reason":"why", "fix":"how"}, {"which_part_of_code":"here1", "reason":"why2", "fix":"how2"}]}'''
    except Exception as e:
        raise HTTPException(status_code=500, detail = f"{e}")

    response = LintResponse(backend=ai, plain_risks="", risks=[])
    if ai == "openai":
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
    uvicorn.run(app, host="127.0.0.1", port=8000)
