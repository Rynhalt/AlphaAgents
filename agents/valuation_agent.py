"""ValuationAgent evaluates price action and relative multiples."""

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


class ValuationAgent(BaseAgent):
    """Produces deterministic valuation metrics using mocked price data."""

    def __init__(self) -> None:
        super().__init__(
            role=AgentRole.VALUATION,
            name="ValuationAgent",
            prompt_file="prompts/valuation.md",
        )
        self._valuation_cache: Dict[str, Dict[str, float]] = {
            "AAPL": {
                "momo_63d": 0.12,
                "realized_vol_21d": 0.23,
                "ma20_above_ma60": 1.0,
                "pe_rel_to_sector": 0.95,
            },
            "MSFT": {
                "momo_63d": 0.08,
                "realized_vol_21d": 0.18,
                "ma20_above_ma60": 1.0,
                "pe_rel_to_sector": 1.05,
            },
            "TSLA": {
                "momo_63d": -0.15,
                "realized_vol_21d": 0.42,
                "ma20_above_ma60": 0.0,
                "pe_rel_to_sector": 1.45,
            },
        }

    async def analyze(
        self,
        ticker: str,
        asof_date: date,
        risk_profile: Optional[str] = None,
    ) -> AgentReport:
        metrics = self._lookup_metrics(ticker)
        llm_stub = self.query_llm({
            "ticker": ticker,
            "risk_profile": risk_profile,
            "asof_date": asof_date.isoformat(),
        })
        metrics["llm_support_score"] = llm_stub["score"]
        decision = self._decide(metrics)
        rationale = self._build_rationale(ticker, metrics, decision)

        evidence = EvidenceRef(
            source=EvidenceSource.PRICE,
            doc_id=f"{ticker.upper()}-PRICE-ANALYSIS",
            span="rolling_metrics",
            snippet="Price momentum positive with supportive trend indicators.",
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
            f"{self.name} highlights momentum {target_report.metrics.get('momo_63d', 0):.2f} "
            f"and relative P/E {target_report.metrics.get('pe_rel_to_sector', 1.0):.2f}."
        )

    async def revise(
        self,
        original_report: AgentReport,
        critiques: List[str],
    ) -> AgentReport:
        revised = original_report.model_copy()
        if critiques:
            revised.rationale = (
                original_report.rationale + " | Adjusted after valuation feedback."
            )
        return revised

    def _lookup_metrics(self, ticker: str) -> Dict[str, float]:
        base_metrics = {
            "momo_63d": 0.0,
            "realized_vol_21d": 0.25,
            "ma20_above_ma60": 0.5,
            "pe_rel_to_sector": 1.0,
        }
        overrides = self._valuation_cache.get(ticker.upper())
        if overrides:
            base_metrics.update(overrides)
        return base_metrics

    def _decide(self, metrics: Dict[str, float]) -> AgentDecision:
        momentum_up = metrics["momo_63d"] > 0
        trend_up = metrics["ma20_above_ma60"] >= 0.5
        valuation_discount = metrics["pe_rel_to_sector"] < 1.0
        if (momentum_up and trend_up) or valuation_discount:
            return AgentDecision.BUY
        if metrics["momo_63d"] < 0 or metrics["pe_rel_to_sector"] > 1.2:
            return AgentDecision.SELL
        return AgentDecision.ABSTAIN

    def _confidence_from_metrics(self, metrics: Dict[str, float]) -> float:
        momo_component = max(0.0, metrics["momo_63d"] + 0.2)
        valuation_component = max(0.0, 1.2 - metrics["pe_rel_to_sector"])
        confidence = 0.4 + momo_component * 0.8 + valuation_component * 0.3
        return round(min(1.0, confidence), 2)

    def _build_rationale(
        self,
        ticker: str,
        metrics: Dict[str, float],
        decision: AgentDecision,
    ) -> str:
        return (
            f"{self.name} finds {decision.value} case for {ticker.upper()} with "
            f"63d momentum {metrics['momo_63d']:.2f} and relative P/E {metrics['pe_rel_to_sector']:.2f}."
        )

    def _build_bullets(self, metrics: Dict[str, float]) -> List[str]:
        trend = "above" if metrics["ma20_above_ma60"] >= 0.5 else "below"
        return [
            f"63-day momentum: {metrics['momo_63d']:.2f}",
            f"21-day realized vol: {metrics['realized_vol_21d']:.2f}",
            f"20-day MA {trend} 60-day MA",
            f"P/E vs sector: {metrics['pe_rel_to_sector']:.2f}",
        ]

    def _detect_red_flags(self, metrics: Dict[str, float]) -> List[str]:
        flags: List[str] = []
        if metrics["momo_63d"] < 0:
            flags.append("Momentum negative.")
        if metrics["pe_rel_to_sector"] > 1.3:
            flags.append("Valuation premium considerable.")
        if metrics["realized_vol_21d"] > 0.35:
            flags.append("Elevated realized volatility.")
        return flags
