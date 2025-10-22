"""Tests for the reasoning trace logger utilities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from eval.reasoning_trace import ReasoningTraceEntry, ReasoningTraceLogger


def test_trace_logger_append_and_read(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    logger = ReasoningTraceLogger(path)

    entry_one = ReasoningTraceEntry(
        session_id="s1",
        agent_role="fundamental",
        stage="critique",
        timestamp=datetime.utcnow(),
        variables={"round": 1},
        result={"content": "first"},
    )
    entry_two = ReasoningTraceEntry(
        session_id="s1",
        agent_role="sentiment",
        stage="revision",
        timestamp=datetime.utcnow(),
        variables={"round": 1},
        result={"content": "second"},
    )

    logger.append(entry_one)
    logger.append(entry_two)

    entries = logger.read()
    assert len(entries) == 2
    assert entries[0].agent_role == "fundamental"
    assert entries[1].stage == "revision"

    tail_entries = logger.tail(1)
    assert len(tail_entries) == 1
    assert tail_entries[0].result["content"] == "second"
