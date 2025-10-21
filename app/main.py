"""FastAPI application entrypoint for AlphaAgents prototype.

See AGENT.md and MILESTONE.md for routing requirements.
"""

from fastapi import FastAPI

app = FastAPI(title="AlphaAgents")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple readiness endpoint used for milestone bootstrap."""
    return {"status": "ok"}

