from haystack import Document
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.writers import DocumentWriter
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.components.generators.chat import OpenAIChatGenerator
from typing import Any, Callable, Dict, List, Optional, Union
from haystack.dataclasses import ChatMessage
from haystack.utils import ComponentDevice, Secret
from haystack import component
import json
import os
import time

from logger import init_logger
#lint.log record all lint messages.
logger = init_logger(__name__, "lint.log")


openai_template = '''

{% if documents %}
Context information is below.
---------------------   
{% for doc in documents %}
    {{ doc.content }}
{% endfor %}
---------------------
Given the context information and not prior knowledge
{% endif %}

you are a expert code reviewer, try your best to  identify *ALL*  possible  risks , each risk has  3 sections, try to  found as many as risks,  and put the most critical on top 
For each section,
 you must obey the following rules:
1. For the code section, MUST show origin code in code section. so I could find where exactly the code is.
2. For the reason describe them as much detail as possible. and give reference web url to justify.
3. For the fix section, ALWAYS use unified diff format, and show the code language

you have two examples to learn:
example 1:

```cpp
void foo(int size) {
	int x[size];
	x[100] = 10;
}
int main(int argc, char** argv) {
	foo(100);
}
```

which_part_of_code: x[100] = 10;
Reason:Accessing an array out of bounds, as the array x is declared with size 'size' but trying to access index 100 which is beyond the array size.
Fix   :```cpp
@@ -1,6 +1,6 @@
 void foo(int size) {
        int x[size];
-       x[100] = 10;
+      x[size - 1] = 10;
 }
 int main(int argc, char** argv) {
        foo(100);
```

example 2:
```python
@app.get("/supported_topics", dependencies=[Depends(verify_header)])
async def supported_topics() -> Response:
    """
    Get the list of supported topics
    """
    return JSONResponse(status_code=200, content={"topics": suppported_topics()})
```

which_part_of_code: return JSONResponse(status_code=200, content={"topics": suppported_topics()})
Reason: typo, suppported_topics is miss spelled 
Fix: 
```python
@@ -1,6 +1,6 @@ a
sync def supported_topics() -> Response:
     """
     Get the list of supported topics
     """
-    return JSONResponse(status_code=200, content={"topics": suppported_topics()})
+    return JSONResponse(status_code=200, content={"topics": supported_topics()})
```

This is the code you want to review:
---------------------
{{code}}
---------------------


'''


templates = {
    "openai":openai_template,
    "custom": openai_template
}


#this could be also use in debug.
#connect PromptBuilder and OpenaiChat
@component
class PromptConvert:
  """
  A component generating personal welcome message and making it upper case
  """
  @component.output_types(messages=List[ChatMessage])
  def run(self, prompt:str):
    logger.debug(prompt)
    return {"messages": [ChatMessage.from_user(prompt)]}


lint_tools = [
    {
        "type": "function",
        "function": {
            "name": "code_potentia_risks",
            "description": "get all risks of the code, and put all risks into array. array size equals the total number of risks",
            "parameters": {
                "type": "object",
                "properties": {
                    "risks":{
                            "type" : "array",
                        "items" :{
                            "type": "object",
                            "properties": {
                                "which_part_of_code": {
                                    "type": "string",
                                    "description": "which part of code is wrong. use the origin code",
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "why this line code has such risk, explain in detail"
                                },
                                "fix": {
                                    "type": "string",
                                    "description": "possible fix for this risk"
                                }
                            }
                        }
                    }
                },
            },
        },
    }
]

import qdrant_client
QDRANT_ADDR="http://localhost:6333"
client = qdrant_client.QdrantClient(
    url = QDRANT_ADDR
)
text_embeder = SentenceTransformersTextEmbedder(model="WhereIsAI/UAE-Large-V1", device=ComponentDevice.from_str("cpu"))
text_embeder.warm_up()



def suppported_topics():
    """
    Get the list of supported topics
    """
    return [cd.name for cd in client.get_collections().collections]

class QueryLint(object):
    def __init__(self, ai):
        #check ai backend
        self.ai = ai
        if not self.ai:
            raise Exception("AI_BACKEND not specifiled")
        if self.ai == "openai":
            self.api_base_url = None
            if "OPENAI_API_KEY" not in os.environ:
                raise Exception("openai should have env OPENAI_API_KEY")
        if self.ai == "custom":
            self.api_base_url = "http://localhost:8081/v1"
            pass

    @staticmethod
    def topic_exist(topic) -> bool:
        return topic in [cd.name for cd in client.get_collections().collections]

    def _build_query_pipe(self, ai:str, ):
        query_pipeline = Pipeline()
        query_pipeline.add_component("prompt_builder", PromptBuilder(template=templates[ai]))
        query_pipeline.add_component("prompt_convert", PromptConvert())
        if self.ai == "openai":
            #only openai supports function call.
            query_pipeline.add_component("llm", OpenAIChatGenerator(model="gpt-3.5-turbo",generation_kwargs={"tools": lint_tools}))
        else:
            #vllm is compatible to openai API.
            #we can use FAKE api_key
            query_pipeline.add_component("llm", OpenAIChatGenerator(api_key=Secret.from_token("FAKE"), model="deepseek-ai/deepseek-coder-7b-instruct-v1.5", api_base_url=self.api_base_url))


        query_pipeline.connect("prompt_builder", "prompt_convert")
        query_pipeline.connect("prompt_convert", "llm")
        return query_pipeline
    
    def _build_rag_query_pipe(self, ai:str, document_store: QdrantDocumentStore):
        query_pipeline = Pipeline()

        query_pipeline.add_component("text_embedder",text_embeder)
        query_pipeline.add_component("retriever", QdrantEmbeddingRetriever(document_store=document_store))
        query_pipeline.add_component("prompt_builder", PromptBuilder(template=templates[ai]))
        query_pipeline.add_component("prompt_convert", PromptConvert())


        if self.ai == "openai":
            #only openai supports function call.
            query_pipeline.add_component("llm", OpenAIChatGenerator(model="gpt-3.5-turbo",generation_kwargs={"tools": lint_tools}))
        else:
            #vllm is compatible to openai API.
            query_pipeline.add_component("llm", OpenAIChatGenerator(model="deepseek-ai/deepseek-coder-7b-instruct-v1.5", api_base_url=self.api_base_url))


        query_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
        query_pipeline.connect("retriever", "prompt_builder.documents")
        query_pipeline.connect("prompt_builder", "prompt_convert")
        query_pipeline.connect("prompt_convert", "llm")
        return query_pipeline
    
    def _query_rag(self, topic: str, code: str):
        #BUG: this QdrantDocumentStore will ALWAYS create collection
        document_store = QdrantDocumentStore(
           QDRANT_ADDR,
           embedding_dim=1024,
           index = topic,
        )
        query_pipeline = self._build_rag_query_pipe(self.ai, document_store)
        result = query_pipeline.run({
                "text_embedder": {"text": code},
                "retriever": {"top_k": 3},
                "prompt_builder":{"code": code}
        })
        return self.handle_response(result)

    def handle_response(self, result) -> str:
        if self.ai != "openai":
            return result["llm"]["replies"][0].content
        #only one funciton is called for extracting data.
        function_call = json.loads(result["llm"]["replies"][0].content)[0]
        logger.debug(function_call)
        function_args = function_call['function']['arguments']
        """
        sample: ["risks":[{which_part_of_code, reason, fix},...]]
        """
        return function_args


    def _query(self, code: str):
        query_pipeline = self._build_query_pipe(self.ai)
        result = query_pipeline.run({
            "prompt_builder" :{"code": code, "documents": []}
        })
        return self.handle_response(result)

        
    def query_lint(self, topic: str, code :str):
        start = time.time()
        if self.topic_exist(topic):
            ret= self._query_rag(topic, code)
        
        ret = self._query(code)
        logger.info(f"lint code len:{len(code)}, dur:{time.time() - start:.2f}")
        return ret


if __name__ == "__main__":
    with open("../../client/april/src/llm_client.rs") as f:
        code = f.read()
    index = QueryLint("openai")
    print(index.query_lint("XXX", code))
