from __future__ import annotations

from app.core.request_context import RequestContext
from app.domain.enums import RouteMode, ToolName
from app.domain.models import GroundedAnswer, RagEvidence, RoutingDecision, ToolPlan, ToolResult
from app.orchestration.graph import BankingAssistantGraph
from app.orchestration.policies import RoutingPolicy


class FixedRouter:
    def __init__(self, decision: RoutingDecision) -> None:
        self.decision = decision

    async def route(self, message: str) -> RoutingDecision:
        return self.decision.model_copy(deep=True)


class RecordingBanking:
    def __init__(self, result: ToolResult | None = None) -> None:
        self.calls: list[ToolPlan] = []
        self.result = result

    async def execute(self, context: RequestContext, plan: ToolPlan) -> ToolResult:
        self.calls.append(plan)
        if self.result is not None:
            return self.result
        return ToolResult(name=plan.name, ok=True, data={"available_balance": 100.0, "currency": "MAD"})


class RecordingRetriever:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def retrieve(self, query: str) -> list[RagEvidence]:
        self.queries.append(query)
        return [RagEvidence(chunk_id="c1", source="policy.md", content="approved policy", score=0.9)]


class DeterministicAnswer:
    async def generate(self, **kwargs) -> GroundedAnswer:
        return GroundedAnswer(answer="grounded")


class InMemoryAudit:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def record(self, *, context: RequestContext, event: str, metadata: dict[str, object]) -> None:
        self.events.append(event)


def build(decision: RoutingDecision, banking: RecordingBanking, retriever: RecordingRetriever) -> BankingAssistantGraph:
    return BankingAssistantGraph(
        router=FixedRouter(decision),
        banking=banking,
        retriever=retriever,
        answer_generator=DeterministicAnswer(),
        audit=InMemoryAudit(),
        policy=RoutingPolicy(),
    )


async def test_balance_uses_tool_without_rag() -> None:
    banking, retriever = RecordingBanking(), RecordingRetriever()
    graph = build(
        RoutingDecision(mode=RouteMode.TOOLS_ONLY, tools=[ToolPlan(name=ToolName.GET_ACCOUNT_BALANCE)]),
        banking,
        retriever,
    )
    await graph.invoke({"request_id": "r1", "customer_id": "C1024", "conversation_id": "c1", "message": "balance", "trace": []})
    assert [c.name for c in banking.calls] == [ToolName.GET_ACCOUNT_BALANCE]
    assert retriever.queries == []


async def test_policy_uses_rag_without_tool() -> None:
    banking, retriever = RecordingBanking(), RecordingRetriever()
    graph = build(
        RoutingDecision(mode=RouteMode.RAG_ONLY, rag_query="international transfer fees"),
        banking,
        retriever,
    )
    await graph.invoke({"request_id": "r1", "customer_id": "C1024", "conversation_id": "c1", "message": "fees", "trace": []})
    assert banking.calls == []
    assert len(retriever.queries) == 1


async def test_hybrid_tool_success_then_rag() -> None:
    result = ToolResult(
        name=ToolName.GET_TRANSFER_STATUS,
        ok=True,
        data={"status": "REJECTED", "rejection_reason": "PAYMENT_LIMIT_EXCEEDED", "amount": 1000},
    )
    banking, retriever = RecordingBanking(result), RecordingRetriever()
    graph = build(
        RoutingDecision(
            mode=RouteMode.HYBRID,
            tools=[ToolPlan(name=ToolName.GET_TRANSFER_STATUS, transfer_id="TR4587")],
            rag_query="rejected transfer resolution",
        ),
        banking,
        retriever,
    )
    state = await graph.invoke({"request_id": "r1", "customer_id": "C1024", "conversation_id": "c1", "message": "rejected", "trace": []})
    assert len(banking.calls) == 1
    assert len(retriever.queries) == 1
    assert "PAYMENT_LIMIT_EXCEEDED" in retriever.queries[0]
    assert "1000" not in retriever.queries[0]  # amount is deliberately minimized out of the RAG query
    assert state["trace"].index("tools:1") < state["trace"].index("rag:1")


async def test_hybrid_tool_failure_skips_rag() -> None:
    failed = ToolResult(name=ToolName.GET_TRANSFER_STATUS, ok=False, safe_error="not found")
    banking, retriever = RecordingBanking(failed), RecordingRetriever()
    graph = build(
        RoutingDecision(
            mode=RouteMode.HYBRID,
            tools=[ToolPlan(name=ToolName.GET_TRANSFER_STATUS, transfer_id="TR404")],
            rag_query="rejected transfer resolution",
        ),
        banking,
        retriever,
    )
    await graph.invoke({"request_id": "r1", "customer_id": "C1024", "conversation_id": "c1", "message": "rejected", "trace": []})
    assert len(banking.calls) == 1
    assert retriever.queries == []
