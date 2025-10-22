"""Tests for coordinator LLM consensus explanation."""

from __future__ import annotations

from datetime import date

import pytest

from agents.base_agent import AgentDecision, AgentReport, AgentRole, EvidenceRef, EvidenceSource
from agents.coordinator import Coordinator, CoordinatorAgent


def _basic_report(role: AgentRole, decision: AgentDecision, confidence: float) -> AgentReport:
    return AgentReport(
        ticker="AAPL",
        asof_date=date(2024, 2, 1),
        role=role,
        decision=decision,
        confidence=confidence,
        rationale="sample rationale",
        evidence_refs=[
            EvidenceRef(
                source=EvidenceSource.FILING,
                doc_id="doc",
                span="section",
                snippet="text",
            )
        ],
        metrics={},
    )


def test_coordinator_llm_explanation(monkeypatch):
    reports = [
        _basic_report(AgentRole.FUNDAMENTAL, AgentDecision.BUY, 0.8),
        _basic_report(AgentRole.SENTIMENT, AgentDecision.BUY, 0.7),
        _basic_report(AgentRole.VALUATION, AgentDecision.SELL, 0.6),
    ]

    def mock_query_llm(self, variables):  # type: ignore[override]
        return {
            "content": '{"explanation": "Combined explanation", "confidence": 0.9, "key_points": ["point-1", "point-2"]}',
            "score": 0.9,
            "fallback": False,
        }

    monkeypatch.setattr(CoordinatorAgent, "query_llm", mock_query_llm)

    coordinator = Coordinator()
    consensus = coordinator.aggregate(
        reports,
        ticker="AAPL",
        debate_messages=[{"agent": "fundamental", "content": "critique"}],
        backtest={"sharpe": 1.0},
        session_id="session-test",
    )

    assert consensus.explanation_llm == "Combined explanation"
    assert consensus.metrics["llm_explanation_score"] == pytest.approx(0.9)
    assert consensus.metrics["llm_explanation_fallback"] == 0.0
    assert consensus.explanation_points == ["point-1", "point-2"]
