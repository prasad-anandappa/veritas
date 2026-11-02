"""Data models for Veritas.

The central invariant of the whole project lives here and is enforced by the
agent: **every claim in a finished report carries at least one citation, and
every citation resolves to a source that was actually retrieved.**
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Source(BaseModel):
    """One retrieved, scored source."""

    id: str  # "S1", "S2", ... assigned after dedup, in quality order
    title: str
    url: str
    domain: str
    snippet: str = ""
    content: str = ""  # extracted text the verification pass checks against
    published_date: str | None = None
    sub_question: str = ""  # which sub-question retrieved it
    relevance: float = 0.0  # provider / keyword relevance, 0..1
    authority: float = 0.0  # domain authority, 0..1
    recency: float = 0.0  # publication recency, 0..1
    quality: float = 0.0  # composite quality score, 0..1


class Claim(BaseModel):
    """One atomic factual claim in the report."""

    text: str
    citations: list[str] = Field(default_factory=list)  # source ids, e.g. ["S2"]
    status: str = "unverified"  # verified | flagged
    support: float = 0.0  # verification support score, 0..1
    note: str = ""  # why it was flagged, when it was


class Section(BaseModel):
    """The part of the report answering one sub-question."""

    heading: str  # the sub-question
    claims: list[Claim] = Field(default_factory=list)


class AgentStep(BaseModel):
    tool: str
    detail: str
    status: str = "ok"  # ok | fallback | error


class ReportStats(BaseModel):
    sources_retrieved: int = 0
    sources_used: int = 0
    claims_total: int = 0
    claims_verified: int = 0
    claims_flagged: int = 0
    citation_coverage: float = 0.0  # verified / total claims drafted


class ResearchReport(BaseModel):
    question: str
    mode: str  # mock | live | partial
    search_backend: str
    llm_backend: str
    summary: str = ""
    sub_questions: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    flagged_claims: list[Claim] = Field(default_factory=list)
    stats: ReportStats = Field(default_factory=ReportStats)
    steps: list[AgentStep] = Field(default_factory=list)

    def all_claims(self) -> list[Claim]:
        return [c for s in self.sections for c in s.claims]

    def citation_integrity(self) -> bool:
        """True iff every reported claim is cited and every citation resolves."""
        ids = {s.id for s in self.sources}
        for claim in self.all_claims():
            if not claim.citations:
                return False
            if any(cid not in ids for cid in claim.citations):
                return False
        return True
