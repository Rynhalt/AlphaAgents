"""Tests for BaseAgent.query_llm stub and prompt loading."""

from __future__ import annotations

from datetime import date

from agents.base_agent import AgentRole, BaseAgent, AgentReport, AgentDecision, EvidenceRef, EvidenceSource


class StubAgent(BaseAgent):
    """Minimal agent for exercising LLM stub."""

    async def analyze(self, ticker: str, asof_date: date, risk_profile: str | None = None) -> AgentReport:
        raise NotImplementedError

    async def critique(self, target_report: AgentReport, peer_reports):
        raise NotImplementedError

    async def revise(self, original_report: AgentReport, critiques):
        raise NotImplementedError


def test_query_llm_returns_deterministic_stub(tmp_path) -> None:
    agent = StubAgent(role=AgentRole.FUNDAMENTAL, name="StubAgent", prompt_file="prompts/fundamental.md")
    prompt_text = agent.load_prompt()
    assert "Placeholder prompt" in prompt_text or len(prompt_text) > 0

    first = agent.query_llm({"ticker": "AAPL", "asof": "2024-02-01"})
    second = agent.query_llm({"ticker": "AAPL", "asof": "2024-02-01"})

    assert first == second
    assert first["score"] == second["score"]
    assert first.get("fallback") is True
    assert "[LLM:fundamental]" in first["content"]
