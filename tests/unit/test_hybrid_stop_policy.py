from app.domain.enums import FailureKind, RouteMode, ToolName
from app.domain.models import RoutingDecision, ToolResult
from app.orchestration.graph import BankingAssistantGraph


def test_hybrid_stops_before_rag_when_tool_fails() -> None:
    state = {
        "routing": RoutingDecision(mode=RouteMode.HYBRID, rag_query="policy"),
        "tool_results": [
            ToolResult(
                name=ToolName.GET_TRANSFER_STATUS,
                ok=False,
                failure_kind=FailureKind.NOT_FOUND,
                safe_error="not found",
            )
        ],
    }
    assert BankingAssistantGraph._after_tools(state) == "answer"
