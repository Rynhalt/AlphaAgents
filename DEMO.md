
## Hosted Preview (paused)

- The app currently lives at https://alphaagents.onrender.com/ (free Render tier). If the service sits idle, Render auto-suspends it and it spins back up on first request.
- To protect the student budget, the deployment omits `OPENAI_API_KEY`. Agents run in deterministic fallback mode, so you’ll see the mock narratives rather than live completions.
- To re-enable real calls later: add `OPENAI_API_KEY` in Render’s dashboard, redeploy, then hit `/run_ticker` once so Matplotlib regenerates the PNGs.

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
4. Visit `http://127.0.0.1:8000/`, hard-refresh, and press **Start Session**. That single click runs the full pipeline (LLM fallbacks if `OPENAI_API_KEY` is missing), populates the debate log, and regenerates the Matplotlib charts. No manual `curl` call is needed unless you want to script the demo.

## Demo Assets

| Asset | Description |
|-------|-------------|
| `docs/media/start-session-thumb.png` | Thumbnail shown before the “Start Session” demo link. |
| `docs/media/start-session-demo.mp4` | Recording that shows clicking **Start Session** and the “Analysing…” phase. |
| `docs/media/results-thumb.png` | Thumbnail shown before the “Results walkthrough” link. |
| `docs/media/results-walkthrough.mp4` | Recording that walks through the debate playback, reasoning trace toggle, and coordinator summary. |
| `docs/media/plot-cumulative.png` | Screenshot of the cumulative return plot. |
| `docs/media/plot-rolling-sharpe.png` | Screenshot of the rolling Sharpe plot. |
| `docs/media/plot-drawdown.png` | Screenshot of the drawdown profile. |

### Suggested embedding snippet

```markdown
![Start Session preview](docs/media/start-session-thumb.png)
[▶️ Watch the Start Session demo](docs/media/start-session-demo.mp4)

![Results walkthrough preview](docs/media/results-thumb.png)
[▶️ Watch the results walkthrough](docs/media/results-walkthrough.mp4)

![Cumulative return chart](docs/media/plot-cumulative.png)
![Rolling Sharpe chart](docs/media/plot-rolling-sharpe.png)
![Drawdown chart](docs/media/plot-drawdown.png)
```

### Plot Interpretations

- **Cumulative Return**: Demonstrates the growth of $1 in the equal-weight portfolio produced by the debate. Using the AAPL mock series, the curve trends upward to showcase a positive return profile.
- **Rolling Sharpe (21-day window)**: Illustrates risk-adjusted performance over a monthly horizon. The mock dataset keeps values elevated (≈10+) for visibility; expect lower numbers once real OHLCV data is introduced.
- **Drawdown**: Highlights the depth of peak-to-trough declines. With the gentle mock path, drawdowns stay close to zero, indicating limited downside in the simulated track—real market data will inject more noticeable troughs.

## Known Limitations

- Only the mock tickers (`AAPL`, `MSFT`, `TSLA`) have structured context today.
- LLM calls fall back to deterministic text when the `OPENAI_API_KEY` env var is missing or quota is exhausted.
- The “Live Debate Stream” replays messages after the API call finishes; true streaming will land in a later milestone.
- Render deployment cannot persist the generated PNGs across restarts; re-run `/run_ticker` once per deploy.
