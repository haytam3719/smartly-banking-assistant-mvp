from __future__ import annotations

from uuid import uuid4

from app.domain.enums import RouteMode
from app.domain.models import ChatOutcome
from app.orchestration.graph import BankingAssistantGraph


class ChatService:
    def __init__(self, graph: BankingAssistantGraph, *, expose_debug_trace: bool = False) -> None:
        self.graph = graph
        self.expose_debug_trace = expose_debug_trace

    async def chat(
        self,
        *,
        customer_id: str,
        message: str,
        conversation_id: str | None,
        request_id: str | None,
    ) -> tuple[str, str, ChatOutcome]:
        rid = request_id or str(uuid4())
        cid = conversation_id or str(uuid4())
        state = await self.graph.invoke(
            {
                "request_id": rid,
                "customer_id": customer_id,
                "conversation_id": cid,
                "message": message,
                "trace": [],
            }
        )
        routing = state["routing"]
        citations = self.graph.citations_from_state(state)

        if routing.mode == RouteMode.RAG_ONLY:
            source = "RAG"
        elif routing.mode == RouteMode.TOOLS_ONLY:
            source = "+".join(p.name for p in routing.tools)
        elif routing.mode == RouteMode.HYBRID:
            source = "+".join([*(p.name for p in routing.tools), "RAG"])
        else:
            source = routing.mode

        outcome = ChatOutcome(
            answer=state["grounded_answer"].answer,
            route=routing.mode,
            source=source,
            citations=citations,
            debug_trace=state.get("trace", []) if self.expose_debug_trace else [],
        )
        return rid, cid, outcome
