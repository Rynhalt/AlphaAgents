"""FastAPI application entrypoint for the AlphaAgents prototype."""

from fastapi import FastAPI

app = FastAPI(title="AlphaAgents")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple readiness endpoint used for milestone bootstrap."""
    return {"status": "ok"}


@app.get("/hello")
async def hello() -> dict[str, str]:
    """Return a simple greeting for readiness tests."""
    return {"message": "Hello, World!"}
