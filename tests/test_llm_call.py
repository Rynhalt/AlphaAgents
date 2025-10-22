"""Integration of BaseAgent.query_llm with mocked OpenAI client."""

from __future__ import annotations

import json
from datetime import date

import pytest

from agents.base_agent import AgentRole, BaseAgent, AgentReport, AgentDecision, EvidenceRef, EvidenceSource


class DummyLLMAgent(BaseAgent):
    async def analyze(self, ticker: str, asof_date: date, risk_profile: str | None = None) -> AgentReport:
        raise NotImplementedError

    async def critique(self, target_report: AgentReport, peer_reports):
        raise NotImplementedError

    async def revise(self, original_report: AgentReport, critiques):
        raise NotImplementedError


@pytest.fixture(autouse=True)
def clear_openai_client(monkeypatch):
    monkeypatch.setattr(BaseAgent, "_openai_client", None)


def test_query_llm_uses_openai_when_configured(monkeypatch):
    payload = {"summary": "Mock summary", "score": 0.87}

    class MockCompletion:
        def __init__(self, content: str) -> None:
            self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": content})()})]

    class MockCompletions:
        @staticmethod
        def create(*_, **__):
            return MockCompletion(json.dumps(payload))

    class MockChat:
        completions = MockCompletions()

    class MockClient:
        def __init__(self, *_, **__):
            self.chat = MockChat()

    agent = DummyLLMAgent(role=AgentRole.FUNDAMENTAL, prompt_file="prompts/fundamental.md")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(BaseAgent, "_get_openai_client", staticmethod(lambda: MockClient()))

    result = agent.query_llm({"ticker": "AAPL"})

    assert result["score"] == pytest.approx(0.87)
    assert "Mock summary" in result["content"]
    assert "fallback" not in result
