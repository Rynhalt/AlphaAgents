# AlphaAgents Demo Guide

This guide gives product reviewers a quick tour of the prototype and explains how to replay the demo locally now that the hosted preview is paused.

## Hosted Preview (paused)

- The app was deployed on Render using the free FastAPI web service.
- Live LLM calls quickly consumed the OpenAI quota, so the hosted instance now falls back to the mock responses. To avoid unexpected charges, the Render service is currently disabled.
- My credit card balance was not having it :(

## Local Walkthrough

1. Create the virtual environment (Python 3.9+):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the smoke tests:
   ```bash
   pytest
   ```
3. Start the API (loads `.env` automatically):
   ```bash
   python -m dotenv run -- uvicorn app.main:app --reload
   ```
4. Kick off a debate to populate the plots and consensus data:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/run_ticker \
        -H "Content-Type: application/json" \
        -d '{"ticker": "AAPL", "risk_profile": "risk_neutral"}' | jq
   ```
5. Visit `http://127.0.0.1:8000/`, hard-refresh, and press **Start Session** to watch the debate playback, inspect the reasoning trace, and view the generated plots under *Backtest Metrics*.

## Demo Assets (placeholders)

Store captured media under `docs/media/` and update the table below with actual filenames.

| Asset | Description |
|-------|-------------|
| `docs/media/run-ticker-session.mp4` | Screen recording of starting a session, watching the debate, and revealing the trace. |
| `docs/media/dashboard-overview.png` | Screenshot of the landing page after a completed session. |
| `docs/media/backtest-plots.png` | Screenshot highlighting the Matplotlib charts. |

## Known Limitations

- Only the mock tickers (`AAPL`, `MSFT`, `TSLA`) have structured context today.
- LLM calls fall back to deterministic text when the `OPENAI_API_KEY` env var is missing or quota is exhausted.
- The “Live Debate Stream” replays messages after the API call finishes; true streaming will land in a later milestone.
- Render deployment cannot persist the generated PNGs across restarts; re-run `/run_ticker` once per deploy.

## Next Steps

- Replace mock data with live filings/news/prices once data connectors are enabled.
- Improve the front-end to render agent dialogue with richer formatting.
- Automate regeneration of demo assets whenever major UI changes ship.

