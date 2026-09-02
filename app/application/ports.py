from __future__ import annotations

from typing import Protocol

from app.core.request_context import RequestContext
from app.domain.models import GroundedAnswer, RagEvidence, RoutingDecision, ToolPlan, ToolResult


class RouterPort(Protocol):
    async def route(self, message: str) -> RoutingDecision: ...


class BankingGatewayPort(Protocol):
    async def execute(self, context: RequestContext, plan: ToolPlan) -> ToolResult: ...


class RetrieverPort(Protocol):
    async def retrieve(self, query: str) -> list[RagEvidence]: ...


class AnswerGeneratorPort(Protocol):
    async def generate(
        self,
        *,
        message: str,
        tool_results: list[ToolResult],
        rag_evidence: list[RagEvidence],
        clarification_question: str | None,
        unsupported: bool,
    ) -> GroundedAnswer: ...


class AuditPort(Protocol):
    async def record(self, *, context: RequestContext, event: str, metadata: dict[str, object]) -> None: ...
