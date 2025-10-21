"""Unit tests for the BaseAgent abstract interface."""

from __future__ import annotations

from datetime import date
from typing import Dict, List

import pytest

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    BaseAgent,
    EvidenceRef,
    EvidenceSource,
)


def _blank_report() -> AgentReport:
    return AgentReport(
        ticker="AAPL",
        asof_date=date(2024, 2, 1),
        role=AgentRole.FUNDAMENTAL,
        decision=AgentDecision.BUY,
        confidence=0.5,
        rationale="placeholder",
        evidence_refs=[
            EvidenceRef(
                source=EvidenceSource.FILING,
                doc_id="doc",
                span="p1",
                snippet="snippet text",
            )
        ],
    )


class ProxyAgent(BaseAgent):
    """Overrides abstract methods but delegates directly to the base class."""

    async def analyze(
        self,
        ticker: str,
        asof_date: date,
        risk_profile: str | None = None,
    ) -> AgentReport:
        return await super().analyze(ticker, asof_date, risk_profile)

    async def critique(
        self,
        target_report: AgentReport,
        peer_reports: Dict[AgentRole, AgentReport],
    ) -> str:
        return await super().critique(target_report, peer_reports)

    async def revise(
        self,
        original_report: AgentReport,
        critiques: List[str],
    ) -> AgentReport:
        return await super().revise(original_report, critiques)


class FunctionalAgent(BaseAgent):
    """Concrete subclass that returns deterministic data."""

    async def analyze(
        self,
        ticker: str,
        asof_date: date,
        risk_profile: str | None = None,
    ) -> AgentReport:
        report = _blank_report().model_copy()
        report.ticker = ticker
        report.asof_date = asof_date
        report.role = self.role
        return report

    async def critique(
        self,
        target_report: AgentReport,
        peer_reports: Dict[AgentRole, AgentReport],
    ) -> str:
        return f"{self.role.value} critique for {target_report.ticker}"

    async def revise(
        self,
        original_report: AgentReport,
        critiques: List[str],
    ) -> AgentReport:
        updated = original_report.model_copy()
        updated.rationale = original_report.rationale + " | revised"
        return updated


@pytest.mark.asyncio
async def test_base_agent_methods_raise_when_not_overridden() -> None:
    agent = ProxyAgent(role=AgentRole.FUNDAMENTAL)

    with pytest.raises(NotImplementedError):
        await agent.analyze("AAPL", date(2024, 2, 1))

    with pytest.raises(NotImplementedError):
        await agent.critique(_blank_report(), {})

    with pytest.raises(NotImplementedError):
        await agent.revise(_blank_report(), [])


@pytest.mark.asyncio
async def test_concrete_agent_produces_report() -> None:
    agent = FunctionalAgent(role=AgentRole.SENTIMENT)
    report = await agent.analyze("MSFT", date(2024, 3, 1))
    assert isinstance(report, AgentReport)
    assert report.role is AgentRole.SENTIMENT
    assert report.ticker == "MSFT"
