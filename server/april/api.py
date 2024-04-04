from index import query_lint, AI
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

import uvicorn

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


backend_mapping = {
    "custom": AI.CUSTOM,
    "openai": AI.OPENAI,
    "claude": AI.CLAUDE
}



def veriy_header(request: Request):
    if request.headers.get("Authorization") != os.getenv("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect API key",
            headers={"WWW-Authenticate": "Basic"})
    
        
#@app.post("/query", dependencies=[Depends(verify_credentials)])
@app.post("/query", dependencies=[Depends(veriy_header)])
async def query(request: Request) -> Response:
    """
    Query the LLM model with the given query and return the response
    returns {"message": "response", "refs": ["file1", "file2", ...]}
    """
    try: 
        request_dict = await request.json()
        topic = request_dict.pop("topic")
        query = request_dict.pop("query")
        ai = backend_mapping[request_dict.pop("ai")]
    except Exception as e:
        return JSONResponse(status_code=400, content={'message': f"invalid request, missing {e}"})
    
    try: 
        response = query_lint(ai, topic, query)
    except Exception as e:
        return JSONResponse(status_code=500, content={'message': f"internal error: {e}"})
    #for debug
    # if hasattr(response, 'metadata'):
    #     print(response.metadata)
    return handle_response(response)


def handle_response(llm_response) -> str:
    #debug
    answer = llm_response.response
    #filter the answer from the response
    #find the location of 'Answer: \n" in the response, and return the text after that
    keyword = "Answer: \n" #keyword comes from the prompt template in llama.index. this keyword may change.
    response = {}
    response["message"] = answer[answer.find(keyword) + len(keyword):]
    response["refs"] = [value['file_name'] for value in llm_response.metadata.values()]
    print(response)
    return response

#uvicorn --reload --port 8000 api:app
#TODO add arguments
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)