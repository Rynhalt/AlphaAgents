"""Tests for ValuationAgent deterministic output."""

from __future__ import annotations

from datetime import date

import pytest

from agents.base_agent import AgentDecision
from agents.valuation_agent import ValuationAgent


@pytest.mark.asyncio
async def test_valuation_agent_buy_signal_with_positive_momentum() -> None:
    agent = ValuationAgent()
    report = await agent.analyze("AAPL", date(2024, 2, 1))
    assert report.decision is AgentDecision.BUY
    assert report.metrics["momo_63d"] > 0
    assert "63-day momentum" in report.bullets[0]
    assert "llm_support_score" in report.metrics
    assert "[LLM:valuation]" in report.rationale


@pytest.mark.asyncio
async def test_valuation_agent_sell_on_negative_momentum() -> None:
    agent = ValuationAgent()
    report = await agent.analyze("TSLA", date(2024, 2, 1))
    assert report.decision is AgentDecision.SELL
    assert any("Momentum negative" in flag for flag in report.red_flags)


@pytest.mark.asyncio
async def test_valuation_agent_defaults_to_abstain() -> None:
    agent = ValuationAgent()
    report = await agent.analyze("UNKNOWN", date(2024, 2, 1))
    assert report.decision is AgentDecision.ABSTAIN
    assert report.metrics["pe_rel_to_sector"] == pytest.approx(1.0)
