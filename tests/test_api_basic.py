"""Basic FastAPI endpoint tests for AlphaAgents."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_hello_returns_200() -> None:
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}  # test: response payload


def test_run_agent_returns_dummy_report() -> None:
    response = client.get("/run_agent", params={"ticker": "AAPL"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    assert payload["decision"] == "BUY"
    assert 0.0 <= payload["confidence"] <= 1.0


def test_run_consensus_returns_all_reports() -> None:
    response = client.get("/run_consensus", params={"ticker": "AAPL"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    consensus = payload["consensus"]
    assert consensus["final_decision"] in {"BUY", "SELL"}
    per_role = consensus["per_role"]
    assert set(per_role.keys()) == {"fundamental", "sentiment", "valuation"}
    assert len(payload["reports"]) == 3
