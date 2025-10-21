"""Schema validation tests for core AlphaAgents models."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    Consensus,
    EvidenceRef,
    EvidenceSource,
)


def _sample_evidence() -> EvidenceRef:
    return EvidenceRef(
        source=EvidenceSource.FILING,
        doc_id="AAPL-10K-2023",
        span="p.17 para 3",
        snippet="Revenue guidance improved year over year.",
        timestamp=datetime(2024, 1, 5, 12, 0, 0),
    )


def _sample_report() -> AgentReport:
    return AgentReport(
        ticker="AAPL",
        asof_date=date(2024, 2, 1),
        role=AgentRole.FUNDAMENTAL,
        decision=AgentDecision.BUY,
        confidence=0.82,
        rationale="Demand improving across product lines.",
        bullets=["Revenue growth stabilizing"],
        evidence_refs=[_sample_evidence()],
        red_flags=["Margin compression risk"],
        metrics={"guidance_tone_score": 0.35},
    )


def test_agentreport_schema_fields_exist() -> None:
    report = _sample_report()
    assert report.ticker == "AAPL"
    assert report.role == AgentRole.FUNDAMENTAL
    assert 0.0 <= report.confidence <= 1.0
    assert report.metrics["guidance_tone_score"] == 0.35
    assert report.evidence_refs[0].source is EvidenceSource.FILING


def test_agentreport_confidence_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        AgentReport(
            ticker="MSFT",
            asof_date=date(2024, 2, 1),
            role=AgentRole.SENTIMENT,
            decision=AgentDecision.SELL,
            confidence=1.5,  # out of range
            rationale="Confidence out of range should fail.",  # test: raises ValidationError
        )


def test_consensus_requires_buy_or_sell() -> None:
    report = _sample_report()
    consensus = Consensus(
        ticker="AAPL",
        asof_date=date(2024, 2, 1),
        final_decision=AgentDecision.BUY,
        conviction=0.7,
        explanation="Majority BUY decision.",
        consolidated_evidence=[_sample_evidence()],
        per_role={report.role: report},
    )
    assert consensus.final_decision is AgentDecision.BUY
    assert consensus.per_role[AgentRole.FUNDAMENTAL].decision is AgentDecision.BUY

    with pytest.raises(ValidationError):
        Consensus(
            ticker="AAPL",
            asof_date=date(2024, 2, 1),
            final_decision=AgentDecision.ABSTAIN,
            conviction=0.5,
            explanation="ABSTAIN not allowed for consensus.",
        )


def test_evidence_ref_snippet_constraints() -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(
            source=EvidenceSource.NEWS,
            doc_id="NEWS-1",
            span="lines 10-12",
            snippet=" ",  # whitespace-only should fail
        )

