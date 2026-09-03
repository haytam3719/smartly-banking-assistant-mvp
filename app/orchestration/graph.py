from __future__ import annotations

import asyncio
import json
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.application.ports import AnswerGeneratorPort, AuditPort, BankingGatewayPort, RetrieverPort, RouterPort
from app.core.request_context import RequestContext
from app.domain.enums import EvidenceType, RouteMode, ToolName
from app.domain.models import Citation
from app.orchestration.policies import RoutingPolicy
from app.orchestration.state import AssistantState


class BankingAssistantGraph:
    def __init__(
        self,
        *,
        router: RouterPort,
        banking: BankingGatewayPort,
        retriever: RetrieverPort,
        answer_generator: AnswerGeneratorPort,
        audit: AuditPort,
        policy: RoutingPolicy,
        checkpointer: Any | None = None,
    ) -> None:
        self.router = router
        self.banking = banking
        self.retriever = retriever
        self.answer_generator = answer_generator
        self.audit = audit
        self.policy = policy
        self.graph = self._build().compile(checkpointer=checkpointer)

    def _build(self) -> StateGraph:
        graph = StateGraph(AssistantState)
        graph.add_node("route", self._route)
        graph.add_node("tools", self._tools)
        graph.add_node("prepare_hybrid_rag", self._prepare_hybrid_rag)
        graph.add_node("rag", self._rag)
        graph.add_node("answer", self._answer)

        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route",
            self._after_route,
            {
                "rag": "rag",
                "tools": "tools",
                "answer": "answer",
            },
        )
        graph.add_conditional_edges(
            "tools",
            self._after_tools,
            {
                "hybrid_rag": "prepare_hybrid_rag",
                "answer": "answer",
            },
        )
        graph.add_edge("prepare_hybrid_rag", "rag")
        graph.add_edge("rag", "answer")
        graph.add_edge("answer", END)
        return graph

    async def _route(self, state: AssistantState) -> dict[str, object]:
        decision = self.policy.validate(await self.router.route(state["message"]))
        await self._audit(state, "route_decided", {"mode": decision.mode, "tools": [p.name for p in decision.tools]})
        return {"routing": decision, "trace": [*state.get("trace", []), f"route:{decision.mode}"]}

    @staticmethod
    def _after_route(state: AssistantState) -> str:
        mode = state["routing"].mode
        if mode == RouteMode.RAG_ONLY:
            return "rag"
        if mode in {RouteMode.TOOLS_ONLY, RouteMode.HYBRID}:
            return "tools"
        return "answer"

    async def _tools(self, state: AssistantState) -> dict[str, object]:
        ctx = self._context(state)
        plans = state["routing"].tools
        results = await asyncio.gather(*(self.banking.execute(ctx, plan) for plan in plans))
        await self._audit(
            state,
            "tools_completed",
            {"tools": [r.name for r in results], "success": [r.ok for r in results]},
        )
        return {"tool_results": list(results), "trace": [*state.get("trace", []), f"tools:{len(results)}"]}

    @staticmethod
    def _after_tools(state: AssistantState) -> str:
        if state["routing"].mode != RouteMode.HYBRID:
            return "answer"
        if any(not result.ok for result in state.get("tool_results", [])):
            # Do not explain a customer-specific failure with generic policy when the dynamic fact is unavailable.
            return "answer"
        return "hybrid_rag"

    async def _prepare_hybrid_rag(self, state: AssistantState) -> dict[str, object]:
        base = state["routing"].rag_query or state["message"]
        facts: list[dict[str, object]] = []
        for result in state.get("tool_results", []):
            if not result.ok or not result.data:
                continue
            # Minimize customer data sent to the retrieval query. We only keep fields
            # that help select a policy, never balances or transaction lists.
            if result.name == ToolName.GET_TRANSFER_STATUS:
                facts.append({
                    "tool": result.name,
                    "status": result.data.get("status"),
                    "rejection_reason": result.data.get("rejection_reason"),
                })
            elif result.name == ToolName.GET_CARD_INFO:
                facts.append({
                    "tool": result.name,
                    "card_type": result.data.get("card_type"),
                    "status": result.data.get("status"),
                })
        enriched = f"{base}\n\nVerified policy-selection facts:\n{json.dumps(facts, ensure_ascii=False, default=str)}"
        return {"rag_query": enriched, "trace": [*state.get("trace", []), "hybrid:tool_facts_added"]}

    async def _rag(self, state: AssistantState) -> dict[str, object]:
        query = state.get("rag_query") or state["routing"].rag_query or state["message"]
        evidence = await self.retriever.retrieve(query)
        await self._audit(state, "rag_completed", {"chunks": len(evidence), "sources": sorted({e.source for e in evidence})})
        return {"rag_evidence": evidence, "trace": [*state.get("trace", []), f"rag:{len(evidence)}"]}

    async def _answer(self, state: AssistantState) -> dict[str, object]:
        routing = state["routing"]
        result = await self.answer_generator.generate(
            message=state["message"],
            tool_results=state.get("tool_results", []),
            rag_evidence=state.get("rag_evidence", []),
            clarification_question=routing.clarification_question,
            unsupported=routing.mode == RouteMode.UNSUPPORTED,
        )
        await self._audit(state, "answer_generated", {"insufficient_evidence": result.insufficient_evidence})
        return {"grounded_answer": result, "trace": [*state.get("trace", []), "answer"]}

    async def invoke(self, initial: AssistantState) -> AssistantState:
        config = {"configurable": {"thread_id": initial["conversation_id"]}}
        return await self.graph.ainvoke(initial, config=config)

    @staticmethod
    def _context(state: AssistantState) -> RequestContext:
        return RequestContext(
            request_id=state["request_id"],
            customer_id=state["customer_id"],
            conversation_id=state["conversation_id"],
        )

    async def _audit(self, state: AssistantState, event: str, metadata: dict[str, object]) -> None:
        await self.audit.record(context=self._context(state), event=event, metadata=metadata)

    @staticmethod
    def citations_from_state(state: AssistantState) -> list[Citation]:
        citations: list[Citation] = []
        for result in state.get("tool_results", []):
            citations.append(Citation(type=EvidenceType.TOOL, name=result.name))
        for chunk in state.get("rag_evidence", []):
            citations.append(
                Citation(type=EvidenceType.RAG, name=chunk.source, chunk_id=chunk.chunk_id, score=chunk.score)
            )
        return citations
