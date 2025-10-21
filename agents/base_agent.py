"""Shared data models and enums used across AlphaAgents."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


#These will be used, to indicate which type of evidence each agent used
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """Fallback StrEnum for Python < 3.11."""

        def __str__(self) -> str:
            return str(self.value)


class EvidenceSource(StrEnum):
    """Supported evidence origin types used by agent reports."""

    FILING = "filing"
    TRANSCRIPT = "transcript"
    NEWS = "news"
    PRICE = "price"

#Defining different agents
class AgentRole(StrEnum):
    """Enumerates the canonical agent roles in the system."""

    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    VALUATION = "valuation"

#Defining Decision of each Agents, short or long position
class AgentDecision(StrEnum):
    """Permitted agent-level investment decisions."""

    BUY = "BUY"
    SELL = "SELL"
    ABSTAIN = "ABSTAIN"

#Initializing a class of Evidence Ref and class function - these contain the actual refences and a sneakpeak to the said source.
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

"""
Modelling the output of each Agents - for example, every report should have an assocaited ticker,
associated date, a role (like technical), and decisin, and rational as a string,
and list of arguments and pieces of evidence

"""

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

"""
Modelling the output of the entire framework - the consensus.
Similar to AgentReport Class, but now it has a specific explanation, as well as associated reports and agents
"""
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
