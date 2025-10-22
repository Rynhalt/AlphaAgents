"""Coordinator aggregates agent reports into a consensus decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Iterable, List, Sequence

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    Consensus,
    EvidenceRef,
)


@dataclass
class Coordinator:
    """Compute consensus decisions from individual agent reports."""

    risk_profile: str = "risk_neutral"

    def aggregate(
        self,
        reports: Sequence[AgentReport],
        ticker: str,
        asof_date: date | None = None,
    ) -> Consensus:
        if not reports:
            msg = "Coordinator requires at least one AgentReport."
            raise ValueError(msg)

        per_role = {report.role: report for report in reports}
        if len(per_role) != len(reports):
            msg = "Duplicate agent roles detected when computing consensus."
            raise ValueError(msg)

        buy_reports = [report for report in reports if report.decision is AgentDecision.BUY]
        sell_reports = [report for report in reports if report.decision is AgentDecision.SELL]

        final_decision = self._resolve_decision(buy_reports, sell_reports)
        conviction = self._compute_conviction(final_decision, buy_reports, sell_reports)
        explanation = self._build_explanation(final_decision, buy_reports, sell_reports)
        evidence = self._collect_evidence(final_decision, buy_reports, sell_reports)

        first_report = reports[0]
        consensus_date = asof_date or first_report.asof_date

        return Consensus(
            ticker=ticker.upper(),
            asof_date=consensus_date,
            final_decision=final_decision,
            conviction=conviction,
            explanation=explanation,
            consolidated_evidence=evidence,
            per_role=per_role,
        )

    def _resolve_decision(
        self,
        buy_reports: Sequence[AgentReport],
        sell_reports: Sequence[AgentReport],
    ) -> AgentDecision:
        if len(buy_reports) > len(sell_reports):
            return AgentDecision.BUY
        if len(sell_reports) > len(buy_reports):
            return AgentDecision.SELL

        if not buy_reports and not sell_reports:
            return AgentDecision.SELL

        return self._break_tie(buy_reports, sell_reports)

    def _break_tie(
        self,
        buy_reports: Sequence[AgentReport],
        sell_reports: Sequence[AgentReport],
    ) -> AgentDecision:
        profile = (self.risk_profile or "risk_neutral").lower()
        if profile == "risk_averse":
            return AgentDecision.SELL

        buy_conf = sum(report.confidence for report in buy_reports)
        sell_conf = sum(report.confidence for report in sell_reports)
        if buy_conf - sell_conf > 0.4:
            return AgentDecision.BUY
        return AgentDecision.SELL

    @staticmethod
    def _compute_conviction(
        final_decision: AgentDecision,
        buy_reports: Sequence[AgentReport],
        sell_reports: Sequence[AgentReport],
    ) -> float:
        target_reports = buy_reports if final_decision is AgentDecision.BUY else sell_reports
        if not target_reports:
            return 0.0
        return round(mean(report.confidence for report in target_reports), 2)

    @staticmethod
    def _build_explanation(
        final_decision: AgentDecision,
        buy_reports: Sequence[AgentReport],
        sell_reports: Sequence[AgentReport],
    ) -> str:
        buy_summary = ", ".join(f"{report.role.value}:{report.confidence:.2f}" for report in buy_reports)
        sell_summary = ", ".join(f"{report.role.value}:{report.confidence:.2f}" for report in sell_reports)
        explanation_parts = [
            f"BUY votes ({len(buy_reports)}): {buy_summary or 'none'}",
            f"SELL votes ({len(sell_reports)}): {sell_summary or 'none'}",
            f"Final decision: {final_decision.value}",
        ]
        return " | ".join(explanation_parts)

    @staticmethod
    def _collect_evidence(
        final_decision: AgentDecision,
        buy_reports: Sequence[AgentReport],
        sell_reports: Sequence[AgentReport],
    ) -> List[EvidenceRef]:
        target_reports: Iterable[AgentReport]
        target_reports = buy_reports if final_decision is AgentDecision.BUY else sell_reports
        evidence: List[EvidenceRef] = []
        for report in target_reports:
            evidence.extend(report.evidence_refs)
            if len(evidence) >= 5:
                break
        return evidence[:5]
