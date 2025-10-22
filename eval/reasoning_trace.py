"""Utilities for logging and reading agent reasoning traces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel


class ReasoningTraceEntry(BaseModel):
    """Structured record of a single LLM prompt/response cycle."""

    session_id: str
    agent_role: str
    stage: str
    timestamp: datetime
    variables: Dict[str, Any]
    result: Dict[str, Any]


@dataclass
class ReasoningTraceLogger:
    """Append-only logger for reasoning traces stored as JSONL."""

    path: Path

    def append(self, entry: ReasoningTraceEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")

    def read(self) -> List[ReasoningTraceEntry]:
        if not self.path.exists():
            return []
        entries: List[ReasoningTraceEntry] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entries.append(ReasoningTraceEntry.model_validate_json(line))
        return entries

    def tail(self, count: int = 5) -> List[ReasoningTraceEntry]:
        return self.read()[-count:]
