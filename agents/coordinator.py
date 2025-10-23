"""Coordinator aggregates agent reports into a consensus decision."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    BaseAgent,
    Consensus,
    EvidenceRef,
)
from eval.reasoning_trace import ReasoningTraceEntry, ReasoningTraceLogger


@dataclass
class Coordinator:
    """Compute consensus decisions from individual agent reports."""

    risk_profile: str = "risk_neutral"
    trace_logger: Optional[ReasoningTraceLogger] = None
    prompt_file: str = "prompts/coordinator.md"

    def aggregate(
        self,
        reports: Sequence[AgentReport],
        ticker: str,
        asof_date: date | None = None,
        debate_messages: Sequence[Dict[str, str]] | None = None,
        backtest: Dict[str, float] | None = None,
        session_id: str | None = None,
    ) -> Consensus:
        if not reports:
            raise ValueError("Coordinator requires at least one AgentReport.")

        per_role = {report.role: report for report in reports}
        if len(per_role) != len(reports):
            raise ValueError("Duplicate agent roles detected when computing consensus.")

        buy_reports = [report for report in reports if report.decision is AgentDecision.BUY]
        sell_reports = [report for report in reports if report.decision is AgentDecision.SELL]

        final_decision = self._resolve_decision(buy_reports, sell_reports)
        conviction = self._compute_conviction(final_decision, buy_reports, sell_reports)
        explanation = self._build_explanation(final_decision, buy_reports, sell_reports)
        evidence = self._collect_evidence(final_decision, buy_reports, sell_reports)

        first_report = reports[0]
        consensus_date = asof_date or first_report.asof_date

        # Generate a narrative explanation leveraging reports, debate log, and backtest summary.
        llm_payload = self._llm_explanation(
            reports=list(per_role.values()),
            debate_messages=debate_messages or [],
            backtest=backtest or {},
            final_decision=final_decision.value,
            session_id=session_id,
        )

        metrics = {
            "llm_explanation_score": llm_payload.get("confidence", 0.0),
            "llm_explanation_fallback": 1.0 if llm_payload.get("fallback", False) else 0.0,
        }

        consensus = Consensus(
            ticker=ticker.upper(),
            asof_date=consensus_date,
            final_decision=final_decision,
            conviction=conviction,
            explanation=explanation,
            consolidated_evidence=evidence,
            per_role=per_role,
        )
        consensus.explanation_llm = llm_payload.get("explanation", "")
        consensus.explanation_points = llm_payload.get("key_points", [])
        consensus.metrics.update(metrics)
        return consensus

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

    def _llm_explanation(
        self,
        reports: List[AgentReport],
        debate_messages: Sequence[Dict[str, str]],
        backtest: Dict[str, float],
        final_decision: str,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        # Use a lightweight coordinator agent so we reuse BaseAgent.query_llm logic.
        coordinator_agent = CoordinatorAgent(prompt_file=self.prompt_file)
        variables = {
            "final_decision": final_decision,
            "reports": [report.model_dump() for report in reports],
            "debate_messages": list(debate_messages),
            "backtest": backtest,
        }
        raw_result = coordinator_agent.query_llm(variables)
        parsed = self._parse_llm_payload(raw_result)
        if session_id:
            logger = self.trace_logger or ReasoningTraceLogger(Path("storage/reasoning_trace.jsonl"))
            self.trace_logger = logger
            logger.append(
                ReasoningTraceEntry(
                    session_id=session_id,
                    agent_role="coordinator",
                    stage="explanation",
                    timestamp=datetime.utcnow(),
                    variables=variables,
                    result=parsed,
                )
            )
        return parsed

    def _parse_llm_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        # Coordinator responses are expected as JSON strings; fall back gracefully if not.
        content = raw.get("content", "")
        fallback = bool(raw.get("fallback", False))
        confidence = raw.get("score")
        try:
            data = json.loads(content)
            explanation = data.get("explanation", content)
            key_points = data.get("key_points", [])
            confidence = data.get("confidence", confidence)
        except Exception:
            explanation = content
            key_points = []
            fallback = fallback or True
        return {
            "explanation": explanation,
            "key_points": key_points,
            "confidence": confidence or 0.0,
            "fallback": fallback,
            "raw_response": content,
        }


class CoordinatorAgent(BaseAgent):
    """Thin wrapper so the coordinator can call BaseAgent.query_llm."""

    def __init__(self, prompt_file: str):
        super().__init__(role=AgentRole.COORDINATOR, name="CoordinatorAgent", prompt_file=prompt_file)

    async def analyze(self, ticker: str, asof_date: date, risk_profile: str | None = None):  # pragma: no cover - unused
        raise NotImplementedError

    async def critique(self, target_report: AgentReport, peer_reports):  # pragma: no cover - unused
        raise NotImplementedError

    async def revise(self, original_report: AgentReport, critiques):  # pragma: no cover - unused
        raise NotImplementedError
