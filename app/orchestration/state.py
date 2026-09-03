from __future__ import annotations

from typing_extensions import TypedDict

from app.domain.models import GroundedAnswer, RagEvidence, RoutingDecision, ToolResult


class AssistantState(TypedDict, total=False):
    request_id: str
    customer_id: str
    conversation_id: str
    message: str
    routing: RoutingDecision
    tool_results: list[ToolResult]
    rag_query: str
    rag_evidence: list[RagEvidence]
    grounded_answer: GroundedAnswer
    trace: list[str]
