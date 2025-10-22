"""Tests validating the SentimentAgent mock behavior."""

from __future__ import annotations

from datetime import date

import pytest

from agents.base_agent import AgentDecision
from agents.sentiment_agent import SentimentAgent


@pytest.mark.asyncio
async def test_sentiment_agent_buy_bias_for_positive_score() -> None:
    agent = SentimentAgent()
    report = await agent.analyze("AAPL", date(2024, 2, 1))
    assert report.decision is AgentDecision.BUY
    assert report.metrics["sentiment_score"] > 0
    assert "Sentiment score" in report.bullets[0]
    assert "llm_support_score" in report.metrics
    assert report.metrics["llm_fallback"] in {0.0, 1.0}
    assert "[LLM:sentiment]" in report.rationale


@pytest.mark.asyncio
async def test_sentiment_agent_sell_on_negative_score() -> None:
    agent = SentimentAgent()
    report = await agent.analyze("TSLA", date(2024, 2, 1))
    assert report.decision is AgentDecision.SELL
    assert any("Negative news tone" in flag for flag in report.red_flags)


@pytest.mark.asyncio
async def test_sentiment_agent_risk_averse_threshold() -> None:
    agent = SentimentAgent()
    report = await agent.analyze("AAPL", date(2024, 2, 1), risk_profile="risk_averse")
    assert report.decision is AgentDecision.ABSTAIN
    assert report.metrics["sentiment_score"] == pytest.approx(0.22)


@pytest.mark.asyncio
async def test_sentiment_agent_defaults_for_unknown_ticker() -> None:
    agent = SentimentAgent()
    report = await agent.analyze("UNKNOWN", date(2024, 2, 1))
    assert report.decision is AgentDecision.ABSTAIN
    assert report.metrics["news_count"] == 20
