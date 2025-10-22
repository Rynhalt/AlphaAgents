"""Integration tests for the /run_ticker endpoint."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_run_ticker_pipeline_creates_outputs(tmp_path) -> None:
    consensus_path = Path("storage/consensus.jsonl")
    debate_path = Path("storage/debate_log.jsonl")

    prior_consensus_lines = consensus_path.read_text(encoding="utf-8").strip().splitlines() if consensus_path.exists() else []
    prior_debate_lines = debate_path.read_text(encoding="utf-8").strip().splitlines() if debate_path.exists() else []

    response = client.post("/run_ticker", json={"ticker": "AAPL", "risk_profile": "risk_neutral"})
    assert response.status_code == 200
    data = response.json()

    assert "session_id" in data
    session_id = data["session_id"]
    assert data["ticker"] == "AAPL"
    assert len(data["reports"]) == 3
    assert "consensus" in data
    assert data["consensus"]["final_decision"] in {"BUY", "SELL"}
    assert "backtest" in data
    plots = data["backtest"]["plots"]
    cumulative_plot = Path("app/static/plots") / Path(plots["cumulative"]).name
    rolling_plot = Path("app/static/plots") / Path(plots["rolling_sharpe"]).name
    assert cumulative_plot.exists()
    assert rolling_plot.exists()

    # Validate consensus log appended this session
    if consensus_path.exists():
        new_lines = consensus_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(new_lines) >= len(prior_consensus_lines)
        last_record = json.loads(new_lines[-1])
        assert last_record["session_id"] == session_id

    # Validate debate logs appended
    if debate_path.exists():
        new_lines = debate_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(new_lines) >= len(prior_debate_lines)
        last_record = json.loads(new_lines[-1])
        assert last_record["session_id"] == session_id

