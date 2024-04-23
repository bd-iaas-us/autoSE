from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.vllm import VllmServer
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.openai import OpenAI
from llama_index.core import PromptTemplate
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import Response as LlamaIndexResponse
import qdrant_client
import os
import sys

from enum import Enum

class AI(Enum):
    CUSTOM = 1
    OPENAI = 2
    CLAUDE = 3



#exam environment variables ANTHROPIC_API_KEY and OPENAI_API_KEY

if 'ANTHROPIC_API_KEY' not in os.environ or 'OPENAI_API_KEY' not in os.environ:
    raise ValueError("Please set the ANTHROPIC_API_KEY and OPENAI_API_KEY")
else:
    #debug
    print(f"claude key is {os.environ['ANTHROPIC_API_KEY']}")
    print(f"gpt key is {os.environ['OPENAI_API_KEY']}")



# vllm load model
# use this to test vllm server
# curl -XPOST http://localhost:8000/generate -d'{"prompt":"hello"}'
custom_llm = VllmServer(
   api_url="http://localhost:8000/generate", max_new_tokens=256, temperature=0
)
claude_llm = Anthropic(temperature=0.0, model='claude-3-opus-20240229')
openai_llm = OpenAI(temperature=0.0, model='gpt-3.5-turbo')
Settings.embed_model = HuggingFaceEmbedding(model_name="WhereIsAI/UAE-Large-V1", device="cpu")

client = qdrant_client.QdrantClient(
    url = "http://localhost:6333",
)

def suppported_topics():
    """
    Get the list of supported topics
    """
    return [cd.name for cd in client.get_collections().collections]

# try:
#     suppported_topics()
# except Exception as e:
#     print(e)
#     print("Please start the qdrant server")
#     sys.exit(1)

# we should find the best template for the prompt
templates = {
    AI.CLAUDE:"",
    AI.OPENAI:"",
    AI.CUSTOM:""
}




def query_lint(ai: AI, topic: str, query: str):
    if topic == None or topic == "":
        return _query_lint(ai, query)
    return _query_lint_rag(ai, topic, query)



def _query_lint(kind: AI, query: str) -> LlamaIndexResponse:
    """
    Query the LLM model with the given query and return the response,
    no RAG here, client will upload the whole file.
    """
    if kind == AI.CUSTOM:
        llm = custom_llm
    elif kind == AI.OPENAI:
        llm = openai_llm
    elif kind == AI.CLAUDE:
        llm = claude_llm
    else:
        raise ValueError(f"Invalid AI backend type: {kind}")
    prompt = f'''
            Query: {query}\n
            Your response should be in the following format:
            How many risks total, and what are the reasons of the risks, and possible fix of this risk.
            "Answer: \n"
        '''
    response = llm.complete(prompt)
    return LlamaIndexResponse(response=response.text, metadata={})


def _query_lint_rag(kind: AI, topic: str, query: str) -> LlamaIndexResponse:
    """
    Query the LLM model with the given query and return the response,
    prompt template is defined in this function.
    working on the file or project's diff.
    client will upload the file's diff or project's diff.
    """
    #check topic exists
    vector_store = QdrantVectorStore(client=client, collection_name=topic)
    index = VectorStoreIndex.from_vector_store(vector_store)
    if kind == AI.CUSTOM:
        query_engine = index.as_query_engine(llm = custom_llm, response_mode="tree_summarize")
    elif kind == AI.OPENAI:
        query_engine = index.as_query_engine(llm = openai_llm, response_mode="tree_summarize")
    elif kind == AI.CLAUDE:
        query_engine = index.as_query_engine(llm = claude_llm, response_mode="tree_summarize")
    else:
        raise ValueError(f"Invalid AI backend type: {kind}")

    new_summary_tmpl_str = '''
                Context information is below.
                ---------------------
                {context_str}
                ---------------------
                Given the context information and not prior knowledge
                Query: {query_str}\n
                Your response should be in the following format:
                number of risks are ordered.
                ```
                number of risks : reason of risks\n
                ```
                "Answer: \n"
            '''

    query_engine.update_prompts(
        {"response_synthesizer:summary_template": PromptTemplate(new_summary_tmpl_str)}
    )

    #DEBUG
    #display_prompt_dict(query_engine.get_prompts())
    return query_engine.query(query)


# define prompt viewing function
def display_prompt_dict(prompts_dict):
    for k, p in prompts_dict.items():
        print(f"Prompt Key: {k}")
        print(p.get_template())
    
 
# 1. RAG supported. project/file diff model
# 2. RAG supporeed. whole file model: TODO: overlap between local file and  rag file
# 3. RAG not supported. whole file model
if __name__ == "__main__":
    print(suppported_topics())

    querys = ["is snapshot supported? how to snapshot one instance? what's the golang api like?"]
    for q in querys:
        topic = "cannyls-go"
        response = _query_lint_rag(AI.OPENAI, "cannyls-go", q)
        if hasattr(response, 'metadata'):
            print(response.metadata)
        print(response)

    #open local file as a string
    with open("data/cannyls-go/storage/allocator/judy_allocator.go", "r") as f:
        raw_code = f.read()
        prompt = f'''
        Rules:
         User wants a bug free application, can you tell me is there any potential risks or bugs?
        code is below:
        {raw_code}
        '''
    x = _query_lint(AI.OPENAI, prompt)
    print(x)


