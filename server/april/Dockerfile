FROM python:3.10-slim
WORKDIR /workspace
COPY . /workspace
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from haystack.components.embedders import SentenceTransformersDocumentEmbedder;e=SentenceTransformersDocumentEmbedder(model=\"WhereIsAI/UAE-Large-V1\");e.warm_up()"
CMD ["uvicorn", "api:app", "--host", "::", "--port", "8000"]
