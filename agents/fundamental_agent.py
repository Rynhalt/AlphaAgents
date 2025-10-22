"""FundamentalAgent provides mocked fundamentals-driven analysis."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from agents.base_agent import (
    AgentDecision,
    AgentReport,
    AgentRole,
    BaseAgent,
    EvidenceRef,
    EvidenceSource,
)


class FundamentalAgent(BaseAgent):
    """Produces deterministic reports using faux filings metadata."""

    def __init__(self) -> None:
        super().__init__(
            role=AgentRole.FUNDAMENTAL,
            name="FundamentalAgent",
            prompt_file="prompts/fundamental.md",
        )
        self._filings_cache: Dict[str, Dict[str, float]] = {
            "AAPL": {
                "rev_growth_yoy": 0.06,
                "op_margin": 0.29,
                "guidance_tone_score": 0.32,
                "capex_intensity": 0.04,
                "debt_to_equity": 1.5,
            },
            "MSFT": {
                "rev_growth_yoy": 0.09,
                "op_margin": 0.41,
                "guidance_tone_score": 0.24,
                "capex_intensity": 0.08,
                "debt_to_equity": 0.9,
            },
            "TSLA": {
                "rev_growth_yoy": -0.04,
                "op_margin": 0.11,
                "guidance_tone_score": -0.12,
                "capex_intensity": 0.15,
                "debt_to_equity": 1.8,
            },
        }

    async def analyze(
        self,
        ticker: str,
        asof_date: date,
        risk_profile: Optional[str] = None,
    ) -> AgentReport:
        metrics = self._lookup_metrics(ticker)
        llm_stub = self.query_llm({"ticker": ticker, "asof_date": asof_date.isoformat()})
        metrics["llm_support_score"] = llm_stub["score"]
        metrics["llm_fallback"] = 1.0 if llm_stub.get("fallback", False) else 0.0
        decision = self._decide(metrics)
        rationale = self._build_rationale(ticker, metrics, decision)

        evidence = EvidenceRef(
            source=EvidenceSource.FILING,
            doc_id=f"{ticker.upper()}-10K-SIMULATED",
            span="management_discussion",
            snippet="Management commentary indicates steady demand trends.",
            timestamp=datetime.combine(asof_date, datetime.min.time()),
        )

        bullets = self._build_bullets(metrics)
        bullets.append(f"LLM support score: {llm_stub['score']:.2f}")

        return AgentReport(
            ticker=ticker.upper(),
            asof_date=asof_date,
            role=self.role,
            decision=decision,
            confidence=self._confidence_from_metrics(metrics),
            rationale=f"{rationale} | {llm_stub['content']}",
            bullets=bullets,
            evidence_refs=[evidence],
            red_flags=self._detect_red_flags(metrics),
            metrics=metrics,
        )

    async def critique(
        self,
        target_report: AgentReport,
        peer_reports: Dict[AgentRole, AgentReport],
    ) -> str:
        return (
            f"{self.name} notes fundamentals suggest "
            f"{target_report.decision} for {target_report.ticker}."
        )

    async def revise(
        self,
        original_report: AgentReport,
        critiques: List[str],
    ) -> AgentReport:
        revised = original_report.model_copy()
        if critiques:
            revised.rationale = (
                original_report.rationale + " | Incorporated peer feedback."
            )
        return revised

    def _lookup_metrics(self, ticker: str) -> Dict[str, float]:
        base_metrics = {
            "rev_growth_yoy": 0.0,
            "op_margin": 0.18,
            "guidance_tone_score": 0.0,
            "capex_intensity": 0.05,
            "debt_to_equity": 1.2,
        }
        overrides = self._filings_cache.get(ticker.upper())
        if overrides:
            base_metrics.update(overrides)
        return base_metrics

    def _decide(self, metrics: Dict[str, float]) -> AgentDecision:
        tone = metrics["guidance_tone_score"]
        growth = metrics["rev_growth_yoy"]
        margin = metrics["op_margin"]
        if tone >= 0.20 and growth >= 0.0:
            return AgentDecision.BUY
        if tone <= -0.10 or margin < 0.15:
            return AgentDecision.SELL
        return AgentDecision.ABSTAIN

    def _confidence_from_metrics(self, metrics: Dict[str, float]) -> float:
        tone_component = max(0.0, metrics["guidance_tone_score"] + 1) / 2
        margin_component = min(1.0, metrics["op_margin"] / 0.4)
        return round((tone_component + margin_component) / 2, 2)

    def _build_rationale(
        self,
        ticker: str,
        metrics: Dict[str, float],
        decision: AgentDecision,
    ) -> str:
        return (
            f"{self.name} sees {decision.value} bias for {ticker.upper()} "
            f"given tone {metrics['guidance_tone_score']:.2f} and "
            f"revenue growth {metrics['rev_growth_yoy']:.2f}."
        )

    def _build_bullets(self, metrics: Dict[str, float]) -> List[str]:
        return [
            f"Revenue growth YoY: {metrics['rev_growth_yoy']:.2%}",
            f"Operating margin: {metrics['op_margin']:.2%}",
            f"Guidance tone: {metrics['guidance_tone_score']:.2f}",
        ]

    def _detect_red_flags(self, metrics: Dict[str, float]) -> List[str]:
        flags: List[str] = []
        if metrics["rev_growth_yoy"] < 0.0:
            flags.append("Negative revenue growth.")
        if metrics["debt_to_equity"] > 2.0:
            flags.append("Leverage elevated.")
        return flags
