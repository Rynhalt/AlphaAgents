"""Tests for the Coordinator consensus aggregation logic."""

from __future__ import annotations

from datetime import date
from typing import List

import pytest

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    EvidenceRef,
    EvidenceSource,
)
from agents.coordinator import Coordinator


def _make_report(
    role: AgentRole,
    decision: AgentDecision,
    confidence: float,
) -> AgentReport:
    return AgentReport(
        ticker="AAPL",
        asof_date=date(2024, 2, 1),
        role=role,
        decision=decision,
        confidence=confidence,
        rationale=f"{role.value} rationale",
        evidence_refs=[
            EvidenceRef(
                source=EvidenceSource.FILING,
                doc_id=f"{role.value}-doc",
                span="section",
                snippet=f"{role.value} evidence snippet",
            )
        ],
        metrics={"score": confidence},
    )


def test_coordinator_majority_buy() -> None:
    reports: List[AgentReport] = [
        _make_report(AgentRole.FUNDAMENTAL, AgentDecision.BUY, 0.8),
        _make_report(AgentRole.SENTIMENT, AgentDecision.BUY, 0.7),
        _make_report(AgentRole.VALUATION, AgentDecision.SELL, 0.6),
    ]
    coordinator = Coordinator(risk_profile="risk_neutral")
    consensus = coordinator.aggregate(reports, ticker="AAPL")

    assert consensus.final_decision is AgentDecision.BUY
    assert consensus.conviction == pytest.approx(0.75, abs=1e-6)
    assert consensus.per_role[AgentRole.FUNDAMENTAL].decision is AgentDecision.BUY
    assert consensus.consolidated_evidence, "Expected evidence from winning side"


def test_coordinator_tie_break_risk_neutral() -> None:
    reports: List[AgentReport] = [
        _make_report(AgentRole.FUNDAMENTAL, AgentDecision.BUY, 0.6),
        _make_report(AgentRole.SENTIMENT, AgentDecision.SELL, 0.6),
        _make_report(AgentRole.VALUATION, AgentDecision.ABSTAIN, 0.4),
    ]
    coordinator = Coordinator(risk_profile="risk_neutral")
    consensus = coordinator.aggregate(reports, ticker="MSFT")

    assert consensus.final_decision is AgentDecision.SELL
    assert consensus.conviction == pytest.approx(0.6, abs=1e-6)


def test_coordinator_tie_break_buy_with_confidence_delta() -> None:
    reports: List[AgentReport] = [
        _make_report(AgentRole.FUNDAMENTAL, AgentDecision.BUY, 0.9),
        _make_report(AgentRole.SENTIMENT, AgentDecision.SELL, 0.3),
        _make_report(AgentRole.VALUATION, AgentDecision.ABSTAIN, 0.2),
    ]
    coordinator = Coordinator(risk_profile="risk_neutral")
    consensus = coordinator.aggregate(reports, ticker="MSFT")

    assert consensus.final_decision is AgentDecision.BUY
    assert consensus.conviction == pytest.approx(0.9, abs=1e-6)


def test_coordinator_requires_unique_roles() -> None:
    reports: List[AgentReport] = [
        _make_report(AgentRole.FUNDAMENTAL, AgentDecision.BUY, 0.7),
        _make_report(AgentRole.FUNDAMENTAL, AgentDecision.SELL, 0.5),
    ]
    coordinator = Coordinator()
    with pytest.raises(ValueError):
        coordinator.aggregate(reports, ticker="AAPL")

