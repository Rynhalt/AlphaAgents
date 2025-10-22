"""SentimentAgent aggregates mocked news sentiment for equities."""

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


class SentimentAgent(BaseAgent):
    """Generates deterministic sentiment metrics using faux headline data."""

    def __init__(self) -> None:
        super().__init__(
            role=AgentRole.SENTIMENT,
            name="SentimentAgent",
            prompt_file="prompts/sentiment.md",
        )
        self._sentiment_cache: Dict[str, Dict[str, float]] = {
            "AAPL": {
                "sentiment_score": 0.22,
                "news_count": 38,
                "avg_source_quality": 0.74,
                "upgrades": 4,
                "downgrades": 1,
            },
            "MSFT": {
                "sentiment_score": 0.18,
                "news_count": 42,
                "avg_source_quality": 0.68,
                "upgrades": 3,
                "downgrades": 0,
            },
            "TSLA": {
                "sentiment_score": -0.21,
                "news_count": 55,
                "avg_source_quality": 0.61,
                "upgrades": 1,
                "downgrades": 5,
            },
        }
    # Main entry point function of the agent
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
        metrics["llm_fallback"] = 1.0 if llm_stub.get("fallback", False) else 0.0
        decision = self._decide(metrics, risk_profile)
        rationale = self._build_rationale(ticker, metrics, decision)

        evidence = EvidenceRef(
            source=EvidenceSource.NEWS,
            doc_id=f"{ticker.upper()}-HEADLINES-SIMULATED",
            span="top_headlines",
            snippet="Headline sentiment tilts positive across major outlets.",
            timestamp=datetime.combine(asof_date, datetime.min.time()),
        )
        #Return fully populated report 
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
            f"{self.name} highlights sentiment score "
            f"{target_report.metrics.get('sentiment_score', 0):.2f} "
            f"for {target_report.ticker}."
        )

    async def revise(
        self,
        original_report: AgentReport,
        critiques: List[str],
    ) -> AgentReport:
        revised = original_report.model_copy()
        if critiques:
            revised.rationale = (
                original_report.rationale + " | Updated after sentiment feedback."
            )
        return revised

    def _lookup_metrics(self, ticker: str) -> Dict[str, float]:
        base_metrics = {
            "sentiment_score": 0.0,
            "news_count": 20,
            "avg_source_quality": 0.6,
            "upgrades": 1,
            "downgrades": 1,
        }
        overrides = self._sentiment_cache.get(ticker.upper())
        if overrides:
            base_metrics.update(overrides)
        return base_metrics
    # Mapping sentiment score to decide if a stock is a buy or a sell
    def _decide(
        self,
        metrics: Dict[str, float],
        risk_profile: Optional[str],
    ) -> AgentDecision:
        score = metrics["sentiment_score"]
        threshold = 0.15 if risk_profile != "risk_averse" else 0.25
        if score >= threshold:
            return AgentDecision.BUY
        if score <= -0.15:
            return AgentDecision.SELL
        return AgentDecision.ABSTAIN

    def _confidence_from_metrics(self, metrics: Dict[str, float]) -> float:
        base_conf = (metrics["sentiment_score"] + 1) / 2
        quality_bonus = metrics["avg_source_quality"] * 0.2
        return round(min(1.0, max(0.0, base_conf + quality_bonus)), 2)

    def _build_rationale(
        self,
        ticker: str,
        metrics: Dict[str, float],
        decision: AgentDecision,
    ) -> str:
        return (
            f"{self.name} notes sentiment score {metrics['sentiment_score']:.2f} "
            f"with {int(metrics['news_count'])} headlines supporting {decision.value}."
        )

    def _build_bullets(self, metrics: Dict[str, float]) -> List[str]:
        return [
            f"Sentiment score: {metrics['sentiment_score']:.2f}",
            f"Headlines analyzed: {int(metrics['news_count'])}",
            f"Upgrades vs Downgrades: {int(metrics['upgrades'])} / {int(metrics['downgrades'])}",
        ]

    def _detect_red_flags(self, metrics: Dict[str, float]) -> List[str]:
        flags: List[str] = []
        if metrics["sentiment_score"] < -0.1:
            flags.append("Negative news tone dominates.")
        if metrics["downgrades"] > metrics["upgrades"]:
            flags.append("Analyst downgrades outweigh upgrades.")
        return flags
