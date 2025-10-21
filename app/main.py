"""FastAPI application entrypoint for the AlphaAgents prototype."""

from datetime import date

from fastapi import FastAPI

from agents.dummy_agent import DummyAgent

app = FastAPI(title="AlphaAgents")
dummy_agent = DummyAgent()


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
