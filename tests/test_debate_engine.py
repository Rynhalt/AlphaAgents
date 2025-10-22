"""Tests for the LLM-backed DebateEngine implementation."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict

import pytest

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    BaseAgent,
    EvidenceRef,
    EvidenceSource,
)
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


class MockAgent(BaseAgent):
    """LLM stub that echoes stage and round."""

    def __init__(self, role: AgentRole):
        super().__init__(role=role, prompt_file="prompts/fundamental.md")

    async def analyze(self, ticker: str, asof_date: date, risk_profile: str | None = None):  # pragma: no cover
        raise NotImplementedError

    async def critique(self, target_report: AgentReport, peer_reports):  # pragma: no cover
        raise NotImplementedError

    async def revise(self, original_report: AgentReport, critiques):  # pragma: no cover
        raise NotImplementedError

    def query_llm(self, variables):  # type: ignore[override]
        stage = variables["stage"]
        round_index = variables["round"]
        assert "context" in variables
        assert len(variables["context"]) > 0
        return {
            "content": f"{self.role.value}-{stage}-round{round_index}",
            "score": 0.9,
            "fallback": False,
        }


def test_debate_engine_emits_llm_messages(tmp_path: Path) -> None:
    reports: Dict[AgentRole, AgentReport] = {
        AgentRole.FUNDAMENTAL: _build_report(AgentRole.FUNDAMENTAL, 0.8),
        AgentRole.SENTIMENT: _build_report(AgentRole.SENTIMENT, 0.6),
        AgentRole.VALUATION: _build_report(AgentRole.VALUATION, 0.7),
    }
    agents = {role: MockAgent(role) for role in reports}
    trace_path = tmp_path / "trace.jsonl"
    engine = DebateEngine(max_rounds=2, trace_path=trace_path)
    messages = engine.run(agents, reports, session_id="session-123")

    assert len(messages) == 9  # 3 critiques + 3 revisions + 3 critiques
    stages = [msg.stage for msg in messages]
    assert stages[:3] == ["critique", "critique", "critique"]
    assert stages[3:6] == ["revision", "revision", "revision"]
    assert stages[6:] == ["critique", "critique", "critique"]
    for message in messages:
        assert message.score == 0.9
        assert message.fallback is False
        assert message.content

    trace_lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(trace_lines) >= 6  # critiques + revisions from round 1


def test_debate_engine_requires_reports() -> None:
    engine = DebateEngine()
    with pytest.raises(ValueError):
        engine.run({}, {})


def test_stream_messages_format() -> None:
    reports = {AgentRole.FUNDAMENTAL: _build_report(AgentRole.FUNDAMENTAL, 0.8)}
    agents = {AgentRole.FUNDAMENTAL: MockAgent(AgentRole.FUNDAMENTAL)}
    engine = DebateEngine(max_rounds=1)
    messages = engine.run(agents, reports)
    stream = list(stream_messages(messages))
    assert stream
    assert stream[0].startswith("data: ")
    assert stream[0].strip().endswith("}")
