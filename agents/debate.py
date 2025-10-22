"""Mock DebateEngine orchestrating critique-revision dialogue among agents."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, Iterable, Iterator, List, Sequence

from pydantic import BaseModel

from agents.base_agent import AgentReport, AgentRole


class DebateMessage(BaseModel):
    """Single message emitted during a debate round."""

    round: int
    agent: str
    content: str
    timestamp: datetime


@dataclass
class DebateEngine:
    """Coordinates a two-round critique and revision loop."""

    max_rounds: int = 2
    turn_order: Sequence[AgentRole] = field(
        default_factory=lambda: (
            AgentRole.FUNDAMENTAL,
            AgentRole.SENTIMENT,
            AgentRole.VALUATION,
        )
    )

    def run(
        self,
        reports: Dict[AgentRole, AgentReport],
    ) -> List[DebateMessage]:
        """Perform a fixed number of critique rounds and collect messages."""
        if not reports:
            msg = "DebateEngine.run requires at least one AgentReport."
            raise ValueError(msg)

        messages: Deque[DebateMessage] = deque()
        current_reports = reports.copy()

        critiques_per_round: List[Dict[AgentRole, str]] = []

        for round_index in range(1, self.max_rounds + 1):
            critiques = self._run_critiques(round_index, current_reports)
            critiques_per_round.append(critiques)
            messages.extend(self._messages_from_critiques(round_index, critiques))

            if round_index >= self.max_rounds:
                break

            current_reports = self._apply_revisions(
                round_index,
                current_reports,
                critiques,
                messages,
            )

        return list(messages)

    def _run_critiques(
        self,
        round_index: int,
        reports: Dict[AgentRole, AgentReport],
    ) -> Dict[AgentRole, str]:
        critiques: Dict[AgentRole, str] = {}
        for role in self.turn_order:
            report = reports.get(role)
            if not report:
                continue
            peer_reports = {peer_role: r for peer_role, r in reports.items() if peer_role != role}
            critiques[role] = (
                f"{role.value} critique round {round_index}: "
                f"confidence {report.confidence:.2f}, peers {[p.value for p in peer_reports]}."
            )
        return critiques

    def _messages_from_critiques(
        self,
        round_index: int,
        critiques: Dict[AgentRole, str],
    ) -> Iterable[DebateMessage]:
        timestamp = datetime.utcnow()
        for role, content in critiques.items():
            yield DebateMessage(
                round=round_index,
                agent=role.value,
                content=content,
                timestamp=timestamp,
            )

    def _apply_revisions(
        self,
        round_index: int,
        reports: Dict[AgentRole, AgentReport],
        critiques: Dict[AgentRole, str],
        messages: Deque[DebateMessage],
    ) -> Dict[AgentRole, AgentReport]:
        updated_reports: Dict[AgentRole, AgentReport] = {}
        for role, report in reports.items():
            critique_messages = [critique for agent, critique in critiques.items() if agent != role]
            revised = report.model_copy()
            if critique_messages:
                revised.rationale = (
                    f"{report.rationale} | Round {round_index} feedback considered."
                )
            updated_reports[role] = revised
            timestamp = datetime.utcnow()
            messages.append(
                DebateMessage(
                    round=round_index,
                    agent=f"{role.value}-revision",
                    content=f"{role.value} revised their rationale.",
                    timestamp=timestamp,
                )
            )
        return updated_reports


def stream_messages(messages: Iterable[DebateMessage]) -> Iterator[str]:
    """Yield Server-Sent Event formatted strings for streaming responses."""
    for message in messages:
        yield f"data: {message.model_dump_json()}\n\n"
