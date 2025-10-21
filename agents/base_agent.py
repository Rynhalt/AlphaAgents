"""Shared data models, enums, and base agent abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

try:  # Python < 3.11 fallback
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """Minimal StrEnum replacement for older Python versions."""

        def __str__(self) -> str:
            return str(self.value)


class EvidenceSource(StrEnum):
    """Supported evidence origin types used by agent reports."""

    FILING = "filing"
    TRANSCRIPT = "transcript"
    NEWS = "news"
    PRICE = "price"


class AgentRole(StrEnum):
    """Enumerates the canonical agent roles in the system."""

    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    VALUATION = "valuation"


class AgentDecision(StrEnum):
    """Permitted agent-level investment decisions."""

    BUY = "BUY"
    SELL = "SELL"
    ABSTAIN = "ABSTAIN"


class EvidenceRef(BaseModel):
    """Reference to supporting evidence selected by an agent."""

    source: EvidenceSource
    doc_id: str
    span: str
    snippet: str = Field(max_length=200)
    timestamp: Optional[datetime] = None

    @field_validator("snippet")
    @classmethod
    def ensure_snippet_not_empty(cls, value: str) -> str:
        if not value.strip():
            msg = "snippet must contain non-whitespace characters"
            raise ValueError(msg)
        return value


class AgentReport(BaseModel):
    """Structured output returned by each domain-specific agent."""

    ticker: str
    asof_date: date
    role: AgentRole
    decision: AgentDecision
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    bullets: List[str] = Field(default_factory=list)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)

    @field_validator("bullets", "red_flags", mode="after")
    @classmethod
    def strip_empty_strings(cls, items: List[str]) -> List[str]:
        return [item for item in items if item.strip()]


class Consensus(BaseModel):
    """Final aggregated decision emitted by the coordinator."""

    ticker: str
    asof_date: date
    final_decision: AgentDecision
    conviction: float = Field(ge=0.0, le=1.0)
    explanation: str
    consolidated_evidence: List[EvidenceRef] = Field(default_factory=list)
    per_role: Dict[AgentRole, AgentReport] = Field(default_factory=dict)

    @field_validator("final_decision")
    @classmethod
    def restrict_final_decision(cls, value: AgentDecision) -> AgentDecision:
        if value is AgentDecision.ABSTAIN:
            msg = "final_decision must be BUY or SELL"
            raise ValueError(msg)
        return value


class BaseAgent(ABC):
    """Abstract agent interface used by all domain-specific agents."""

    def __init__(self, role: AgentRole, name: Optional[str] = None) -> None:
        self.role = role
        self.name = name or f"{role.value.title()}Agent"

    @abstractmethod
    async def analyze(
        self,
        ticker: str,
        asof_date: date,
        risk_profile: Optional[str] = None,
    ) -> AgentReport:
        """Produce an initial AgentReport for the requested ticker."""
        raise NotImplementedError

    @abstractmethod
    async def critique(
        self,
        target_report: AgentReport,
        peer_reports: Dict[AgentRole, AgentReport],
    ) -> str:
        """Return textual feedback for a peer AgentReport."""
        raise NotImplementedError

    @abstractmethod
    async def revise(
        self,
        original_report: AgentReport,
        critiques: List[str],
    ) -> AgentReport:
        """Generate a revised AgentReport after receiving critiques."""
        raise NotImplementedError
