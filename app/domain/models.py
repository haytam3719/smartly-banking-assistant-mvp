from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import EvidenceType, FailureKind, RouteMode, ToolName


class ToolPlan(BaseModel):
    name: ToolName
    transfer_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int | None = Field(default=None, ge=1, le=100)


class RoutingDecision(BaseModel):
    mode: RouteMode
    tools: list[ToolPlan] = Field(default_factory=list)
    rag_query: str | None = None
    clarification_question: str | None = None
    rationale: str = Field(default="", max_length=500)


class ToolResult(BaseModel):
    name: ToolName
    ok: bool
    data: dict[str, Any] | None = None
    failure_kind: FailureKind | None = None
    safe_error: str | None = None
    latency_ms: int = 0


class RagEvidence(BaseModel):
    chunk_id: str
    source: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    type: EvidenceType
    name: str
    chunk_id: str | None = None
    score: float | None = None


class GroundedAnswer(BaseModel):
    answer: str
    insufficient_evidence: bool = False


class ChatOutcome(BaseModel):
    answer: str
    route: RouteMode
    source: str
    citations: list[Citation]
    debug_trace: list[str] = Field(default_factory=list)
