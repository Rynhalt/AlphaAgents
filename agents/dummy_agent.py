"""Deterministic agent used for early pipeline testing."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    BaseAgent,
    EvidenceRef,
    EvidenceSource,
)


class DummyAgent(BaseAgent):
    """Simple agent returning hard-coded but schema-compliant data."""

    def __init__(self) -> None:
        super().__init__(role=AgentRole.FUNDAMENTAL, name="DummyAgent")

    async def analyze(
        self,
        ticker: str,
        asof_date: date,
        risk_profile: str | None = None,
    ) -> AgentReport:
        evidence = EvidenceRef(
            source=EvidenceSource.FILING,
            doc_id=f"{ticker}-DUMMY-001",
            span="summary",
            snippet="Placeholder evidence supporting the dummy BUY decision.",
            timestamp=datetime.combine(asof_date, datetime.min.time()),
        )
        return AgentReport(
            ticker=ticker,
            asof_date=asof_date,
            role=self.role,
            decision=AgentDecision.BUY,
            confidence=0.75,
            rationale="DummyAgent recommends BUY for testing purposes.",
            bullets=["Revenue growth improving", "Margins stable"],
            evidence_refs=[evidence],
            red_flags=["Synthetic data only"],
            metrics={"dummy_score": 0.8},
        )

    async def critique(
        self,
        target_report: AgentReport,
        peer_reports: Dict[AgentRole, AgentReport],
    ) -> str:
        return f"{self.name} has no critique for {target_report.ticker}."

    async def revise(
        self,
        original_report: AgentReport,
        critiques: List[str],
    ) -> AgentReport:
        revised = original_report.model_copy()
        if critiques:
            revised.rationale = (
                f"{original_report.rationale} | Adjusted after critiques."
            )
        return revised

