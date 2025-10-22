"""Tests for the FundamentalAgent mock implementation."""

from __future__ import annotations

from datetime import date

import pytest

from agents.base_agent import AgentDecision
from agents.fundamental_agent import FundamentalAgent

#For now, the outputs from fundamental agents are deterministic, so it expects 
# A specific output given a particular input

@pytest.mark.asyncio
async def test_fundamental_agent_returns_buy_for_positive_metrics() -> None:
    agent = FundamentalAgent()
    report = await agent.analyze("AAPL", date(2024, 2, 1))
    assert report.decision is AgentDecision.BUY
    assert report.metrics["guidance_tone_score"] > 0
    assert "Revenue growth YoY" in report.bullets[0]
    assert "llm_support_score" in report.metrics
    assert report.metrics["llm_fallback"] in {0.0, 1.0}
    assert "[LLM:fundamental]" in report.rationale


@pytest.mark.asyncio
async def test_fundamental_agent_flags_negative_growth() -> None:
    agent = FundamentalAgent()
    report = await agent.analyze("TSLA", date(2024, 2, 1))
    assert report.decision is AgentDecision.SELL
    assert any("Negative revenue growth" in flag for flag in report.red_flags)


@pytest.mark.asyncio
async def test_fundamental_agent_defaults_to_abstain() -> None:
    agent = FundamentalAgent()
    report = await agent.analyze("UNKNOWN", date(2024, 2, 1))
    assert report.decision is AgentDecision.ABSTAIN
    assert report.confidence <= 1.0
