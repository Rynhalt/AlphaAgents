# AlphaAgents

This personal project by Marcus Izumi explores a prototype of multi-agent framework used for stock evaluation, inspired by BlackRock’s August 2025 research note on multi-agent LLM systems for equity portfolios:
- *AlphaAgents: Large Language Model based Multi-Agents for Equity Portfolio Constructions*
- https://arxiv.org/html/2508.11152v1

The paper sketches a debate-driven ensemble of domain agents (fundamental, sentiment, valuation) that iteratively critique each other before a coordinator forms a trade decision. It highlights promising backtest results and governance benefits, but it ships no reference code or architectural deep dive. I started this repository to reverse-engineer the described workflow, fill in the missing technical details, and learn what it would take to operationalize such a system end to end.

---

  ## Features 

  - LLM-driven agents for fundamental, sentiment, and valuation analysis—each generates structured reports (decision, confidence, rationale,
    metrics) with OpenAI fallback.
  - Debate engine runs two critique/revision rounds, streams messages via SSE, and logs every prompt/response to storage/
    reasoning_trace.jsonl.
  - Coordinator synthesizes the final consensus (majority vote + tie-breaker) and, when the key is available, calls the LLM for a narrative
    and bullet points; falls back gracefully otherwise.
  - Portfolio backtester builds equal-weight portfolios off the consensus, runs a mock return simulation, and saves Matplotlib plots
    (cumulative_return.png, rolling_sharpe.png).
  - Front-end (FastAPI + Jinja) includes risk-profile selection, color-coded live debate stream, collapsible coordinator insights, reasoning
    trace viewer, and auto-refreshing plots.

  👉 **Want a quick tour?** Check out [DEMO.md](DEMO.md) for screenshots, screen recordings, and instructions on replaying the demo locally or via the Render preview link.

  ## Current Status & Limitations

  - The agents currently reason over structured mock data and qualitative heuristics; they do **not** run quantitative valuation models or econometric screens yet, so the output is educational rather than trading-ready.
  - Over the next few weeks I plan to study econometrics/financial time-series methods and fold formal factor models into each agent’s toolset (e.g., DCF variants, cross-sectional regressions, event studies).
  - I am also exploring reinforcement learning hooks—so future iterations can simulate debate policies or portfolio adjustments that learn from reward signals rather than fixed heuristics.

  ---

  ## Architecture

  - app/main.py – FastAPI routes (/run_ticker, /stream/{ticker}, /api/trace/{session_id}, /run_consensus, /health) and SSE streaming.
  - agents/ – Domain agents (*Agent), debate engine (DebateEngine), coordinator, plus shared Pydantic models (reports, consensus).
  - data/mock/ – Per-ticker JSON snippets (filings/news/prices) that feed the mock retriever.
  - data/indices/retriever.py – Loads structured snippets and returns metadata-rich hits.
  - portfolio/ – Backtest utilities and selectors.
  - storage/ – Runtime outputs: consensus/debate logs, reasoning trace, Matplotlib PNGs.

 ```
                  ┌─────────────────────────┐
                  │        Browser UI       │
                  │ (index.html + JS, SSE)  │
                  └─────────────┬─────────-─┘
                                │
                                │ HTTP requests (POST /run_ticker, GET /stream/{ticker}, etc.)
                                │
  ┌─────────────────────────────┴──────────────────────-──────┐
  │                    FastAPI Application                    │
  │                     (app/main.py)                         │
  │                                                           │
  │   ┌─────────────┐        ┌─────────────┐                  │
  │   │ /run_ticker │        │/run_consensus│                 │
  │   └─────┬───────┘        └──────┬───────┘                 │
  │         │ POST JSON              │ GET                    │
  │         │                        │                        │
  │         ▼                        ▼                        │
  │   ┌───────────────┐       ┌───────────-─┐                 │
  │   │ DebateEngine  │       │ Coordinator │                 │
  │   │ (critique +   │       │ (final vote │                 │
  │   │ revisions,    │       │ + LLM expl.)│                 │
  │   │ SSE streaming)│       └─────┬───-───┘                 │
  │   └────┬──────────┘             │                         │
  │        │                        │ Consensus object        │
  │        │ SSE events             │ (decision, rationale,   │
  │        │                        │ explanation_llm, etc.)  │
  │        │                        │                         │
  │        ▼                        │                         │
  │   ┌───────────────────┐ ┌───────▼────────┐                │
  │   │ Agents (Fund/Sent/│ │ Portfolio      │                │
  │   │ Valuation)        │ │ Backtest       │                │
  │   │- BaseAgent.query_ │ │ (equal-weight, │                │
  │   │  llm() w/ fallback│ │ Matplotlib)    │                │
  │   └─────┬─────────────┘ └───────┬────────┘                │
  │         │ inputs                │ outputs                 │
  │         ▼                       ▼                         │
  │   ┌──────────────┐   ┌──────────────────┐  ┌─────────────┐│
  │   │ data/mock/   │   │ storage/         │  │ app/static/ ││
  │   │ structured   │   │ consensus.jsonl  │  │ plots/*.png ││
  │   │ snippets     │   │ debate_log.jsonl |  └─────────────┘│
  │   └──────────────┘   │ reasoning_trace  │                 │
  │                      └──────────────────┘                 │
  └───────────────────────────────────────────────────────────┘
  ```
  ### Legend

  - Browser UI: submits tickers/risk profile, streams live debate, toggles coordinator insight panels.
  - FastAPI: orchestrates agents → debate → coordinator → backtest.
  - Agents: run query_llm with structured context (retriever + debate history) and fall back to deterministic text if needed.
  - Data/mock: ticker-specific JSON (filings/news/prices) loaded by MockRetriever.
  - Storage: logs (consensus, debate, reasoning trace) and Matplotlib outputs saved per run.

  ---

  ## Notes & Caveats

  - Render’s filesystem is ephemeral: PNGs and JSONL logs reset on redeploy. Use external storage if you need persistence.
  - Reasoning trace entries log everything, including fallback responses. /api/trace/{session_id} filters them dynamically.
  - LLM outputs depend on OPENAI_API_KEY. Without it (or with insufficient quota) the UI still runs but shows fallback text.
  - Mock prices/returns are deterministic; to demonstrate dynamic plots, swap in real pricing (e.g., yfinance) or randomize the mock series.

  ---

  ## Next Steps

  1. yfinance / price loader stubs – Add an optional loader that fetches real OHLC/OHLCV windows when enabled, with the current mock pipeline as
     fallback.
  2. External retrieval interface – Sketch a search hook (Perplexity/OpenAI Search) the agents can call; for now, we just wire up the interface
     and keep using mock data.
  3. Econometric models – After a deeper dive into valuation math, wire in factor regressions, discounted cash-flow variants, or cross-sectional signals each agent can call.
  4. Reinforcement learning experiments – Explore policy-gradient style loops where agents learn critique/revision strategies or the portfolio allocator learns position sizing from reward signals.

----

# Debate Engine

```
┌───────────────────────────────  Debate Round  ────────────────────────────────┐
│                                                                               │
│  Step 1: Baseline reports (round 0)                                           │
│                                                                               │
│   ┌──────-──────────┐   ┌────────────────┐   ┌────────────────┐               │
│   │ FundamentalAgent│   │ SentimentAgent │   │ ValuationAgent │               │
│   │  - analyze()    │   │  - analyze()   │   │  - analyze()   │               │
│ - uses MockRetriever│- uses MockRetriever│- uses MockRetriever│               │
│ - falls back on stub│- falls back on stub│- falls back on stub│               │           
│   │    if LLM fails │   │    if LLM fails│   │   if LLM fails │               │
│   └───────-─────────┘   └────────────────┘   └────────────────┘               │
│          │                 │                    │                             │
│          └──── baseline AgentReports (decision + rationale + metrics) ────────┘
│                                                                               │
│  Step 2: Debate round (critique → revision)                                   │
│                                                                               │
│  Critique Phase:                                                              │
│    • DebateEngine iterates in turn order (fundamental → sentiment → valuation)│
│    • For each agent:                                                          │
│        – Gathers:                                                             │
│            reports (self + peers)                                             │
│            debate history (previous messages)                                 │
│            retrieved snippets (MockRetriever.search)                          │
│        – Builds variables {stage: "critique", round: n, ...}                  │
│        – Calls agent.query_llm()                                              │
│        – Logs prompt/response to reasoning_trace                              │
│        – Streams message via SSE (Live Debate Panel)                          │
│                                                                               │
│  Revision Phase:                                                              │
│    • After critiques, each agent revises its report:                          │
│        – Summarizes incoming critiques                                        │
│        – Reuses retriever context                                             │
│        – Calls query_llm() with {stage: "revision", ...}                      │
│        – Updates AgentReport rationale/metrics                                │
│                                                                               │
│  DebateEngine persists:                                                       │
│    – Every message (critique/revision) to storage/debate_log.jsonl            │
│    – Every prompt + response to storage/reasoning_trace.jsonl                 │
│                                                                               │
│  Step 3: Repeat round (up to max_rounds, default = 2)                         │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────  Final Consensus  ───────────────────────────────┐
│                                                                               │
│ • Coordinator.aggregate(...) receives updated reports + debate transcript +   │
│   backtest summary                                                            │
│ • LLM explanation:                                                            │
│      – CoordinatorAgent.query_llm() with {reports, debate_messages, backtest} │
│      – Falls back if OpenAI key missing / quota exceeded                      │
│      – Logs to reasoning_trace                                                │
│ • Majority vote / tie-break on BUY / SELL                                     │
│ • consensus.explanation_llm / explanation_points surface on the UI            │
│ • Portfolio backtest uses consensus decision to generate plots                │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘



```

### Quick recap:

  - Each round has two phases: critiques (agents review peers) and revisions (agents update their own report).
  - Every LLM call (agent or coordinator) goes through BaseAgent.query_llm(), pulling context from MockRetriever and falling back to
    deterministic text when necessary.
  - Debate messages stream live to the browser, while richer details (variables, results) are filed in reasoning_trace.jsonl.
  - Once the debate ends, the coordinator synthesizes the final explanation and passes it along with the majority decision to the front-end/
    backtester.

    
# 🏦👾Personal Background / Motivation🍣🛸

Recently, I completed a software engineer internship at an investment bank, and was exposed to equity systems and how technology really intersects with financial markets - and then I heard about this paper.

When reading through the paper, I noticed there was not a lot of technical explanation or code snippets on how the framework was built and explored, so I decided to try to implement them.

The personal goal here, for me, is to be familaized with multi-agentic frameworks, as well as to get a sense of how fundamental, technical and macro analysis are done during the valuation of their stocks.

This project is far from mathematical for now.

The current implementation focuses on architecture, agent interaction, and reasoning flow, not on financial accuracy or quantitative modeling.
