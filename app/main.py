"""FastAPI application entrypoint for the AlphaAgents prototype."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Dict, List

from fastapi import FastAPI

from agents.base_agent import AgentReport
from agents.coordinator import Coordinator
from agents.dummy_agent import DummyAgent
from agents.fundamental_agent import FundamentalAgent
from agents.sentiment_agent import SentimentAgent
from agents.valuation_agent import ValuationAgent

app = FastAPI(title="AlphaAgents")
dummy_agent = DummyAgent()
fundamental_agent = FundamentalAgent()
sentiment_agent = SentimentAgent()
valuation_agent = ValuationAgent()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple readiness endpoint used for milestone bootstrap."""
    return {"status": "ok"}


@app.get("/hello")
async def hello() -> dict[str, str]:
    """Return a simple greeting for readiness tests."""
    return {"message": "Hello, World!"}


@app.get("/run_agent")
async def run_agent(ticker: str) -> dict:
    """Execute DummyAgent for the requested ticker."""
    report = await dummy_agent.analyze(ticker=ticker, asof_date=date.today())
    return report.model_dump()


@app.get("/run_consensus")
async def run_consensus(ticker: str) -> Dict[str, object]:
    """Run all domain agents, then aggregate a consensus decision."""
    asof = date.today()
    reports = await _gather_agent_reports(ticker, asof)
    coordinator = Coordinator()
    consensus = coordinator.aggregate(reports, ticker=ticker, asof_date=asof)
    return {
        "ticker": ticker.upper(),
        "consensus": consensus.model_dump(),
        "reports": [report.model_dump() for report in reports],
    }


async def _gather_agent_reports(ticker: str, asof: date) -> List[AgentReport]:
    """Concurrent helper that executes all domain agents."""
    results = await asyncio.gather(
        fundamental_agent.analyze(ticker, asof),
        sentiment_agent.analyze(ticker, asof),
        valuation_agent.analyze(ticker, asof),
    )
    return list(results)

