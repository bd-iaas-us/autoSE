from index import QueryLint, suppported_topics
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from contextlib import asynccontextmanager

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
    

@app.post("/lint", dependencies=[Depends(veriy_header)])
async def query(request: Request) -> Response:
    """
    Query the LLM model with the given query and return the response
    returns {"message": "response", "refs": ["file1", "file2", ...]}
    """
    try: 
        request_dict = await request.json()
        topic = request_dict.pop("topic")
        code = request_dict.pop("code")
    except Exception as e:
        return JSONResponse(status_code=400, content={'message': f"invalid request, missing {e}"})
    
    try: 
        ai = os.getenv("AI_BACKEND")
        #print(ai, topic, query)
        ql = QueryLint()
        llm_response = ql.query_lint(ai, topic, code)
    except Exception as e:
        return JSONResponse(status_code=500, content={'message': f"internal error: {e}"})

    if ai == "openai":
        #llm_respnose is json-encode string returned from openai
        #response = {"risks":[{"which_part_of_code":"here", "reason":"why", "fix":"how"}, {"which_part_of_code":"here1", "reason":"why2", "fix":"how2"}]}
        response = json.loads(llm_response)
        print(response)
        return JSONResponse(content=response)
    else:
        return handle_custom_response()


def handle_custom_response(llm_response, ai):
    #debug
    answer = llm_response.response
    #filter the answer from the response
    #find the location of 'Answer: \n" in the response, and return the text after that
    keyword = "Answer: \n" #keyword comes from the prompt template in llama.index. this keyword may change.
    response = {}
    response["message"] = answer[answer.find(keyword) + len(keyword):]
    response["refs"] = [value['file_name'] for value in llm_response.metadata.values()]
    return response

#uvicorn --reload --port 8000 api:app
#TODO add arguments
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
