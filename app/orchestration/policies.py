from __future__ import annotations

import re

from app.domain.enums import RouteMode, ToolName
from app.domain.errors import InvalidRoutingPlan
from app.domain.models import RoutingDecision, ToolPlan

TRANSFER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


class RoutingPolicy:
    def __init__(self, max_tools: int = 3) -> None:
        self.max_tools = max_tools

    def validate(self, decision: RoutingDecision) -> RoutingDecision:
        # Deduplicate identical plans while preserving order.
        seen: set[tuple[object, ...]] = set()
        normalized: list[ToolPlan] = []
        for plan in decision.tools:
            key = (plan.name, plan.transfer_id, plan.start_date, plan.end_date, plan.limit)
            if key not in seen:
                seen.add(key)
                normalized.append(plan)

        if len(normalized) > self.max_tools:
            raise InvalidRoutingPlan("Too many tool calls requested")

        if decision.mode == RouteMode.RAG_ONLY and normalized:
            raise InvalidRoutingPlan("RAG_ONLY cannot contain tool plans")

        if decision.mode == RouteMode.TOOLS_ONLY and not normalized:
            raise InvalidRoutingPlan("TOOLS_ONLY requires at least one tool")

        if decision.mode == RouteMode.HYBRID:
            if not normalized:
                raise InvalidRoutingPlan("HYBRID requires at least one tool")
            if not decision.rag_query:
                raise InvalidRoutingPlan("HYBRID requires a RAG query")

        for plan in normalized:
            if plan.name == ToolName.GET_TRANSFER_STATUS:
                if not plan.transfer_id or not TRANSFER_ID_RE.fullmatch(plan.transfer_id):
                    return RoutingDecision(
                        mode=RouteMode.CLARIFY,
                        clarification_question="Pouvez-vous me communiquer la référence du virement ?",
                        rationale="Transfer status requires a valid transfer reference.",
                    )

        decision.tools = normalized
        return decision
