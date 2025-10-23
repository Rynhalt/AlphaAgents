"""FastAPI application entrypoint for the AlphaAgents prototype."""

from __future__ import annotations

import asyncio
from datetime import date
import json
import random
from uuid import uuid4
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents.base_agent import AgentDecision, AgentReport, AgentRole
from agents.coordinator import Coordinator
from agents.debate import DebateEngine, stream_messages
from agents.dummy_agent import DummyAgent
from agents.fundamental_agent import FundamentalAgent
from agents.sentiment_agent import SentimentAgent
from agents.valuation_agent import ValuationAgent
from portfolio.backtest import run_backtest
from portfolio.selector import equal_weight_selection
from pydantic import BaseModel
from eval.reasoning_trace import ReasoningTraceLogger

app = FastAPI(title="AlphaAgents")
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
dummy_agent = DummyAgent()
fundamental_agent = FundamentalAgent()
sentiment_agent = SentimentAgent()
valuation_agent = ValuationAgent()
static_plot_dir = BASE_DIR / "static" / "plots"
storage_dir = Path("storage")
trace_logger = ReasoningTraceLogger(storage_dir / "reasoning_trace.jsonl")


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
async def run_consensus(ticker: str, risk_profile: str = "risk_neutral") -> Dict[str, object]:
    """Run all domain agents, then aggregate a consensus decision."""
    asof = date.today()
    reports = await _gather_agent_reports(ticker, asof, risk_profile=risk_profile)
    coordinator = Coordinator(risk_profile=risk_profile)
    consensus = coordinator.aggregate(
        reports,
        ticker=ticker,
        asof_date=asof,
        debate_messages=[],
        backtest={},
    )
    return {
        "ticker": ticker.upper(),
        "consensus": consensus.model_dump(),
        "reports": [report.model_dump() for report in reports],
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the basic dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/stream/{ticker}")
async def stream_debate(ticker: str, request: Request) -> StreamingResponse:
    """Stream debate messages for the requested ticker."""
    asof = date.today()
    reports_list = await _gather_agent_reports(ticker, asof)
    reports = {report.role: report for report in reports_list}
    agents_map = {
        AgentRole.FUNDAMENTAL: fundamental_agent,
        AgentRole.SENTIMENT: sentiment_agent,
        AgentRole.VALUATION: valuation_agent,
    }
    engine = DebateEngine()
    messages = engine.run(agents_map, reports)
    generator = _sse_generator(messages)
    return StreamingResponse(generator, media_type="text/event-stream")


class RunTickerRequest(BaseModel):
    ticker: str
    risk_profile: str = "risk_neutral"


@app.post("/run_ticker")
async def run_ticker(payload: RunTickerRequest) -> Dict[str, object]:
    """Execute full AlphaAgents pipeline and return aggregated outputs."""
    ticker = payload.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required.")

    session_id = str(uuid4())
    asof = date.today()
    reports = await _gather_agent_reports(ticker, asof, risk_profile=payload.risk_profile)
    reports_by_role = {report.role: report for report in reports}

    debate_engine = DebateEngine()
    agents_map = {
        AgentRole.FUNDAMENTAL: fundamental_agent,
        AgentRole.SENTIMENT: sentiment_agent,
        AgentRole.VALUATION: valuation_agent,
    }
    debate_messages = debate_engine.run(agents_map, reports_by_role, session_id=session_id)

    coordinator = Coordinator(risk_profile=payload.risk_profile)

    buy_reports = [report for report in reports if report.decision is AgentDecision.BUY]
    sell_reports = [report for report in reports if report.decision is AgentDecision.SELL]
    pre_decision = coordinator._resolve_decision(buy_reports, sell_reports)

    decisions = {ticker: pre_decision.value}
    weights = equal_weight_selection(decisions)
    returns = {ticker: _generate_mock_returns(ticker)}

    backtest_result = run_backtest(
        weights,
        returns,
        storage_dir=storage_dir,
        plot_dir=static_plot_dir,
    )

    consensus = coordinator.aggregate(
        reports,
        ticker=ticker,
        asof_date=asof,
        debate_messages=[msg.model_dump() for msg in debate_messages],
        backtest=backtest_result,
        session_id=session_id,
    )

    plot_urls = {
        name: f"/static/plots/{Path(path).name}"
        for name, path in backtest_result.get("plots", {}).items()
    }
    backtest_payload = {**backtest_result, "plots": plot_urls}

    _log_consensus(consensus.model_dump(), session_id)
    _log_debate(debate_messages, session_id)

    response = {
        "session_id": session_id,
        "ticker": ticker,
        "risk_profile": payload.risk_profile,
        "consensus": consensus.model_dump(),
        "reports": [report.model_dump() for report in reports],
        "debate": [message.model_dump() for message in debate_messages],
        "backtest": backtest_payload,
    }
    return response


def _sse_generator(messages: Iterable) -> Iterable[str]:
    """Wrap debate messages into SSE-formatted strings."""
    for chunk in stream_messages(messages):
        yield chunk


@app.get("/api/trace/{session_id}")
async def get_trace(session_id: str) -> Dict[str, Any]:
    """Return reasoning trace entries for a given session."""
    entries = trace_logger.read()
    filtered = [
        entry.model_dump()
        for entry in entries
        if entry.session_id == session_id
    ]
    return {"entries": filtered}


async def _gather_agent_reports(
    ticker: str,
    asof: date,
    *,
    risk_profile: Optional[str] = None,
) -> List[AgentReport]:
    """Concurrent helper that executes all domain agents."""
    results = await asyncio.gather(
        fundamental_agent.analyze(ticker, asof, risk_profile=risk_profile),
        sentiment_agent.analyze(ticker, asof, risk_profile=risk_profile),
        valuation_agent.analyze(ticker, asof, risk_profile=risk_profile),
    )
    return list(results)


def _generate_mock_returns(ticker: str, days: int = 63) -> List[float]:
    """Create deterministic pseudo-returns for backtesting."""
    seed = sum(ord(char) for char in ticker)
    rng = random.Random(seed)
    return [round(rng.uniform(-0.005, 0.015), 5) for _ in range(days)]


def _log_consensus(consensus: Dict[str, object], session_id: str) -> None:
    """Append consensus output to storage jsonl."""
    payload = {**consensus, "session_id": session_id}
    payload["timestamp"] = payload.get("timestamp") or date.today().isoformat()
    _append_jsonl(storage_dir / "consensus.jsonl", payload)


def _log_debate(messages: Iterable, session_id: str) -> None:
    """Persist debate messages to storage jsonl."""
    for message in messages:
        data = message.model_dump()
        data["session_id"] = session_id
        data["timestamp"] = data["timestamp"].isoformat()
        _append_jsonl(storage_dir / "debate_log.jsonl", data)


def _append_jsonl(path: Path, payload: Dict[str, object]) -> None:
    """Append a dictionary as JSON to a jsonl file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")
