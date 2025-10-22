"""Tests for the DebateEngine mock implementation."""

from __future__ import annotations

from datetime import date
from typing import Dict

import pytest

from agents.base_agent import AgentDecision, AgentReport, AgentRole, EvidenceRef, EvidenceSource
from agents.debate import DebateEngine, stream_messages


def _build_report(role: AgentRole, confidence: float) -> AgentReport:
    return AgentReport(
        ticker="AAPL",
        asof_date=date(2024, 2, 1),
        role=role,
        decision=AgentDecision.BUY,
        confidence=confidence,
        rationale=f"{role.value} rationale",
        evidence_refs=[
            EvidenceRef(
                source=EvidenceSource.FILING,
                doc_id=f"{role.value}-doc",
                span="section",
                snippet="Evidence snippet.",
            )
        ],
        metrics={},
    )


def test_debate_engine_emits_messages_for_each_round() -> None:
    reports: Dict[AgentRole, AgentReport] = {
        AgentRole.FUNDAMENTAL: _build_report(AgentRole.FUNDAMENTAL, 0.8),
        AgentRole.SENTIMENT: _build_report(AgentRole.SENTIMENT, 0.6),
        AgentRole.VALUATION: _build_report(AgentRole.VALUATION, 0.7),
    }
    engine = DebateEngine(max_rounds=2)
    messages = engine.run(reports)

    assert len(messages) >= 6  # critiques + revisions across rounds
    for message in messages:
        assert message.round in {1, 2}
        assert isinstance(message.timestamp, type(messages[0].timestamp))
        assert message.agent
        assert message.content


def test_debate_engine_requires_reports() -> None:
    engine = DebateEngine()
    with pytest.raises(ValueError):
        engine.run({})


def test_stream_messages_format() -> None:
    reports = {
        AgentRole.FUNDAMENTAL: _build_report(AgentRole.FUNDAMENTAL, 0.8),
    }
    engine = DebateEngine(max_rounds=1)
    messages = engine.run(reports)
    stream = list(stream_messages(messages))
    assert stream
    assert stream[0].startswith("data: ")
    assert stream[0].strip().endswith("}")

