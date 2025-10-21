"""Tests exercising the DummyAgent implementation."""

from __future__ import annotations

from datetime import date

import pytest

from agents.base_agent import AgentDecision, AgentRole
from agents.dummy_agent import DummyAgent


@pytest.mark.asyncio
async def test_dummyagent_returns_valid_schema() -> None:
    agent = DummyAgent()
    report = await agent.analyze("AAPL", date(2024, 2, 1))

    assert report.ticker == "AAPL"
    assert report.role is AgentRole.FUNDAMENTAL
    assert report.decision is AgentDecision.BUY
    assert 0.0 <= report.confidence <= 1.0
    assert report.metrics["dummy_score"] == pytest.approx(0.8)
    assert report.evidence_refs, "expected at least one evidence reference"

