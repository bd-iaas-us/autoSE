from index import query_engines, general_query
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

import uvicorn

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#curl http://localhost:8080/topics
@app.get("/topics")
async def topics() -> Response:
    """
    Get the list of topics that the API can query
    """
    return {"topics": list(query_engines.keys())}

#curl -XPOST http://localhost:8080/query -d'{"topic":"jedi", "query":"how apiserver talk to scheduler?"}'
@app.post("/query")
async def query(request: Request) -> Response:
    """
    Query the LLM model with the given query and return the response
    returns {"message": "response", "refs": ["file1", "file2", ...]}
    """
    request_dict = await request.json()
    topic = request_dict.pop("topic")
    query = request_dict.pop("query")
    if topic == "general":
        response = general_query(query)
        return {"message": response}
    if topic not in query_engines:
        return JSONResponse(status_code=404, content={"message": "topic not found"})
    llm_resp = query_engines[topic].query(query)

    #filter the answer from the response
    #find the location of 'Answer: \n" in the response, and return the text after that
    keyword = "Answer: \n" #keyword comes from the prompt template in llama.index. this keyword may change.
    response = {}
    response["message"] = llm_resp.response[llm_resp.response.find(keyword) + len(keyword):]
    response["refs"] = [value['file_name'] for value in llm_resp.metadata.values()]
    return response


#uvicorn -p 8080 api:app
#TODO add arguments
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)

