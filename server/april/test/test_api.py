from fastapi.testclient import TestClient
from april.api import app

client = TestClient(app)
def test_query_endpoint_success():
    response = client.post("/query", json={
        "topic": "example",
        "query": "test query",
        "ai": "custom"
    }, headers={"Authorization": "Bearer valid_api_key"})
    assert response.status_code == 200
    assert response.json() == {"message": "response", "refs": ["file1", "file2"]}
def test_query_endpoint_invalid_api_key():
    response = client.post("/query", json={
        "topic": "example",
        "query": "test query",
        "ai": "custom"
    }, headers={"Authorization": "Bearer invalid_api_key"})
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Incorrect API key"
def test_query_endpoint_missing_fields():
    response = client.post("/query", json={
        "topic": "example",
        "ai": "custom"
        # "query" field is missing
    }, headers={"Authorization": "Bearer valid_api_key"})
    assert response.status_code == 400
    assert "message" in response.json()
    assert "invalid request" in response.json()["message"]

