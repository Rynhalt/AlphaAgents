# Debate Flow Walkthrough 

This walkthrough documents how the AlphaAgents debate engine handled an AAPL session as an explanation of how the debate unfolds between agents. The run’s JSONL logs (`storage/consensus.jsonl`, `storage/debate_log.jsonl`, `storage/reasoning_trace.jsonl`) are already uploaded to the repository.

## How the Debate Engine Works
- The DebateEngine cycles through a fixed number of rounds; in each round every agent critiques peers using shared reports, recent debate messages, and retrieved context (`agents/debate.py:46-123`).
- After critiques, `_apply_revisions` fan-outs those comments so each agent revises its own report before the next loop (`agents/debate.py:125-166`).
- Every LLM call (critique, revision, coordinator) is logged to the reasoning trace so we can replay the full prompt/response payload (`agents/debate.py:108`, `agents/debate.py:165`).

## Session Timeline

### Round 1 – Critique Pass
All three agents immediately spot gaps in the initial rationales that were captured in the consensus payload (`storage/consensus.jsonl:1`).

- **Fundamental agent** asks for peer benchmarking and macro framing: “It would be beneficial to compare this growth rate with industry peers … and outline future risks and opportunities more explicitly.” (`storage/debate_log.jsonl:1`)
- **Sentiment agent** presses for nuance behind the topline score and the lone downgrade: “It would be beneficial to explore the nuances behind this score … and delve into the reasons behind the downgrade.” (`storage/debate_log.jsonl:2`)
- **Valuation agent** requests richer relative valuation context: “It would be beneficial to compare this with historical data and competitors’ multiples.” (`storage/debate_log.jsonl:3`)

### Round 1 – Revision Pass
Each agent incorporates the feedback into a revised rationale.

- **Fundamental agent** adds competitive and risk sections that were missing from the original text (which still carried a data-access disclaimer in the initial report, `storage/consensus.jsonl:1`): the revision now calls for “a detailed comparison of Apple’s product offerings … against its key competitors” and elevates “Global Supply Chain and Regulatory Risks” (`storage/debate_log.jsonl:4`).
- **Sentiment agent** reorganizes the narrative into a structured brief, explicitly addressing analyst dynamics and regulatory headwinds named in critique: the revision lays out “Recent analyst upgrades” and a “Risks and Challenges” section covering “global supply chain disruptions … regulatory challenges … Europe and China” (`storage/debate_log.jsonl:5`).
- **Valuation agent** deepens the valuation lens, moving from short momentum notes to a full rundown of “Price-to-Earnings (P/E) Ratio … Discounted Cash Flow scenarios … innovation-driven catalysts,” directly answering the call for comparable metrics (`storage/debate_log.jsonl:6`).

### Round 2 – Final Critique Loop
The second critique-only loop confirms the revisions are on target. Rather than asking for missing sections, each agent now references the enriched arguments, e.g., the fundamental critique recaps the expanded financial context while keeping the BUY stance intact (`storage/debate_log.jsonl:7-9`).

## Reasoning Trace Perspective
The trace shows exactly what inputs fed each LLM call:

```json
{
  "session_id": "83c3cabb-ed80-42aa-bd96-dfcebf8ed5d8",
  "agent_role": "fundamental",
  "stage": "critique",
  "variables": {
    "round": 1,
    "agent_role": "fundamental",
    "ticker": "AAPL",
    "peer_reports_keys": ["sentiment", "valuation"],
    "previous_messages_count": 0
  },
  "result": {
    "score": 0.5,
    "fallback": false,
    "content_excerpt": "The analysis provided by the FundamentalAgent for Apple Inc. (AAPL)..."
  }
}
```

Every entry in `storage/reasoning_trace.jsonl` follows the same schema, including the revision calls (`storage/reasoning_trace.jsonl:4-6`) and the coordinator’s synthesis step (`storage/reasoning_trace.jsonl:10`). All entries report `fallback: false`, confirming live LLM completions throughout the run.

## Coordinator Outcome
After the debate settles, the coordinator aggregates the revised reports into a BUY with 0.73 conviction, citing the same evidence the agents referenced during critique (`storage/consensus.jsonl:1`). Because the JSONL files are versioned, readers can diff future sessions against this baseline to see how revised rationales shift the final call.

## Working with the Uploaded Logs
The committed JSONL artifacts make it easy to:
1. Demonstrate the critique → revision cadence without rerunning the app.
2. Feed a session ID into `/api/trace/{session_id}` during a live server run to stream the same trace data shown here.
3. Compare new debate recordings against this walkthrough to highlight how agent behaviors evolve round by round.
