"""DebateEngine orchestrating critique and revision rounds via LLM calls."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, Iterable, Iterator, List, Optional, Sequence

from pydantic import BaseModel

from agents.base_agent import AgentReport, AgentRole, BaseAgent
from eval.reasoning_trace import ReasoningTraceEntry, ReasoningTraceLogger


class DebateMessage(BaseModel):
    """Single message emitted during a debate round."""

    round: int
    agent: str
    stage: str
    content: str
    score: Optional[float] = None
    fallback: bool = False
    timestamp: datetime


@dataclass
class DebateEngine:
    """Coordinates a two-round critique and revision loop."""

    max_rounds: int = 2
    trace_path: Path = Path("storage/reasoning_trace.jsonl")
    trace_logger: Optional[ReasoningTraceLogger] = None
    turn_order: Sequence[AgentRole] = field(
        default_factory=lambda: (
            AgentRole.FUNDAMENTAL,
            AgentRole.SENTIMENT,
            AgentRole.VALUATION,
        )
    )

    def run(
        self,
        agents: Dict[AgentRole, BaseAgent],
        reports: Dict[AgentRole, AgentReport],
        session_id: Optional[str] = None,
    ) -> List[DebateMessage]:
        """Perform a fixed number of critique rounds and collect messages."""

        if not reports:
            msg = "DebateEngine.run requires at least one AgentReport."
            raise ValueError(msg)

        messages: Deque[DebateMessage] = deque()
        current_reports = {
            role: report.model_copy(deep=True)
            for role, report in reports.items()
        }

        for round_index in range(1, self.max_rounds + 1):
            critique_messages = []
            for role in self.turn_order:
                agent = agents.get(role)
                report = current_reports.get(role)
                if not agent or not report:
                    continue
                peer_reports = {
                    peer_role.value: peer_report.model_dump()
                    for peer_role, peer_report in current_reports.items()
                    if peer_role != role
                }
                variables = {
                    "stage": "critique",
                    "round": round_index,
                    "agent_role": role.value,
                    "ticker": report.ticker,
                    "agent_report": report.model_dump(),
                    "peer_reports": peer_reports,
                    "previous_messages": [msg.model_dump() for msg in messages],
                }
                llm_result = agent.query_llm(variables)
                critique_message = DebateMessage(
                    round=round_index,
                    agent=role.value,
                    stage="critique",
                    content=llm_result["content"],
                    score=llm_result.get("score"),
                    fallback=bool(llm_result.get("fallback", False)),
                    timestamp=datetime.utcnow(),
                )
                messages.append(critique_message)
                critique_messages.append((role, critique_message, llm_result, variables))
                self._log_trace(session_id, role.value, "critique", variables, llm_result)

            if round_index >= self.max_rounds:
                break

            current_reports = self._apply_revisions(
                round_index,
                agents,
                current_reports,
                critique_messages,
                messages,
                session_id,
            )

        return list(messages)

    def _apply_revisions(
        self,
        round_index: int,
        agents: Dict[AgentRole, BaseAgent],
        reports: Dict[AgentRole, AgentReport],
        critiques: List,
        messages: Deque[DebateMessage],
        session_id: Optional[str],
    ) -> Dict[AgentRole, AgentReport]:
        updated_reports: Dict[AgentRole, AgentReport] = {}
        critiques_by_role: Dict[AgentRole, List[DebateMessage]] = {
            role: [] for role in self.turn_order
        }
        for role, message, _, _ in critiques:
            for target_role in critiques_by_role:
                if target_role != role:
                    critiques_by_role[target_role].append(message)

        for role, report in reports.items():
            agent = agents.get(role)
            if not agent:
                updated_reports[role] = report
                continue
            critique_messages = critiques_by_role.get(role, [])
            variables = {
                "stage": "revision",
                "round": round_index,
                "agent_role": role.value,
                "ticker": report.ticker,
                "original_report": report.model_dump(),
                "critiques": [
                    {"agent": msg.agent, "content": msg.content}
                    for msg in critique_messages
                ],
            }
            llm_result = agent.query_llm(variables)
            revised_report = report.model_copy(deep=True)
            revised_report.rationale = llm_result["content"]
            revised_report.metrics["llm_revision_score"] = llm_result.get("score", 0.0)
            revised_report.metrics["llm_revision_fallback"] = 1.0 if llm_result.get("fallback", False) else 0.0
            revision_message = DebateMessage(
                round=round_index,
                agent=role.value,
                stage="revision",
                content=llm_result["content"],
                score=llm_result.get("score"),
                fallback=bool(llm_result.get("fallback", False)),
                timestamp=datetime.utcnow(),
            )
            messages.append(revision_message)
            self._log_trace(session_id, role.value, "revision", variables, llm_result)
            updated_reports[role] = revised_report

        return updated_reports

    def _log_trace(
        self,
        session_id: Optional[str],
        agent_role: str,
        stage: str,
        variables: Dict,
        result: Dict,
    ) -> None:
        if not session_id:
            return
        logger = self.trace_logger
        if logger is None:
            logger = ReasoningTraceLogger(self.trace_path)
            self.trace_logger = logger
        entry = ReasoningTraceEntry(
            session_id=session_id,
            timestamp=datetime.utcnow(),
            agent_role=agent_role,
            stage=stage,
            variables=variables,
            result=result,
        )
        logger.append(entry)


def stream_messages(messages: Iterable[DebateMessage]) -> Iterator[str]:
    """Yield Server-Sent Event formatted strings for streaming responses."""
    for message in messages:
        yield f"data: {message.model_dump_json()}\n\n"
