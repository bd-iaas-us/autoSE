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
from issue import handle_prompt, handle_task, gen_history_data_v2

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


@app.post("/dev", dependencies=[Depends(veriy_header)])
async def createPromptTask(request: Request) -> Response:
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
    
    try:
        request_dict = await request.json()

        # Check if the request is for a project based prompt
        if "prompt" in request_dict:
            return handle_prompt(request_dict)

        return JSONResponse(status_code=400, content={'message': f"The request must contain prompt"})
    except Exception as e:
        return JSONResponse(status_code=400, content={'message': f"invalid request, missing {e}"})

@app.get("/dev/tasks/{taskId}", dependencies=[Depends(veriy_header)])
async def getTaskStatus(taskId) -> Response:
    try: 
        return handle_task(taskId)
    except Exception as e:
        return JSONResponse(status_code=500, content={'message': f"internal server error: {e}"})

#@app.get("/dev/histories/{taskId}", dependencies=[Depends(veriy_header)])
#async def getHistory(taskId, request: Request) -> StreamingResponse:
#    return StreamingResponse(gen_history_data(taskId, request.url))

@app.get("/dev/v2/histories/{taskId}", dependencies=[Depends(veriy_header)])
async def getHistory(taskId, request: Request) -> StreamingResponse:
    return StreamingResponse(gen_history_data_v2(taskId, request.url))


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
        llm_response = QueryLint(ai).query_lint(topic, code)
    except Exception as e:
        return JSONResponse(status_code=500, content={'message': f"internal error: {e}"})

    if ai == "openai":
        #llm_respnose is json-encode string returned from openai
        #response = {"risks":[{"which_part_of_code":"here", "reason":"why", "fix":"how"}, {"which_part_of_code":"here1", "reason":"why2", "fix":"how2"}]}
        response = json.loads(llm_response)
        response["backend"] = ai
        response["plain_risks"] = ""
        logger.debug(response)
        return JSONResponse(content=response)
    else:
        response = {}
        response["backend"] = ai
        response["plain_risks"] = llm_response
        response["risks"] = []
        return JSONResponse(content=response)

#TODO: if llm returns a plain text. maybe we could parse it into a vector of risks.
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
    #asyncio.run(WebSocketServer())
    uvicorn.run(app, host="127.0.0.1", port=8000)
