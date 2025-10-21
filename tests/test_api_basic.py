"""Basic FastAPI endpoint tests for AlphaAgents."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_hello_returns_200() -> None:
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}  # test: response payload

